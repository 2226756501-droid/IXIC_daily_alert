import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger: logging.Logger = logging.getLogger("nasdaq")

from modules.data_fetcher import (
    init_history, load_history, save_history,
    load_config, load_market_state, save_market_state,
    load_memory, save_memory, get_today_data, Record,
)
from modules.analyzer import record_abnormal, finalize_abnormal
from modules.stats import build_memory_advice
from modules.news_fetcher import fetch_nasdaq_news
from modules.config import get_email_config
from modules.agent_engine import generate_email


def main() -> None:
    init_history()
    config: dict[str, Any] = load_config()
    multiplier: float = config["sensitivity_multiplier"]
    msg, pct, data_date, close, change, z_score, open_, high_, low_ = get_today_data(multiplier)
    logger.info(msg)

    records: list[Record] = load_history()
    if not records or records[-1][0] != data_date:
        fetch_time: str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        records.append((data_date, close, change, pct, z_score, open_, high_, low_, fetch_time))
        save_history(records)
        logger.info("已记录 %s 数据", data_date)

    state: dict[str, Any] = load_market_state()
    is_down: bool = pct < 0

    # Collect context for AI email generation
    ctx: dict[str, Any] = {
        "msg": msg, "date": data_date, "pct": pct,
        "close": close, "change": change, "z_score": z_score,
        "is_down": is_down, "state": state.get("state", "normal"),
        "drops": 0, "news": None, "drawdown": None,
        "recovery": False, "advice": None,
    }

    if is_down:
        state["consecutive_drops"] = state.get("consecutive_drops", 0) + 1
        drops: int = state["consecutive_drops"]
        ctx["drops"] = drops

        if drops == 3 and state.get("state") == "normal":
            state["state"] = "abnormal"
            state["abnormal_since"] = data_date
            mem: dict[str, Any] = load_memory()
            mem = record_abnormal(mem, z_score, drops, close, pct, data_date)
            save_memory(mem)
            news_list: list[str] = fetch_nasdaq_news()
            ctx["news"] = news_list if news_list else None

        elif drops >= 4:
            from modules.drawdown import calc_max_drawdown_3m
            dd: dict[str, Any] | None = calc_max_drawdown_3m()
            if dd:
                state["max_drawdown_3m"] = dd
                ctx["drawdown"] = dd

    else:
        if state.get("state") == "abnormal":
            drops = state.get("consecutive_drops", 0)
            ctx["drops"] = drops
            ctx["recovery"] = True
            state["state"] = "normal"
            state["abnormal_since"] = None
            state["consecutive_drops"] = 0
            state["max_drawdown_3m"] = None
            mem = load_memory()
            mem = finalize_abnormal(mem, data_date, drops)
            save_memory(mem)
        else:
            state["consecutive_drops"] = 0

    save_market_state(state)

    drops = state.get("consecutive_drops", 0)
    if is_down and drops >= 2 and z_score <= -1.5:
        mem = load_memory()
        advice: str = build_memory_advice(mem.get("events", []), z_score, drops)
        if advice:
            ctx["advice"] = advice

    subject, body = build_email(ctx)
    send_email(subject, body)
    logger.info("邮件已发送")


def build_email(ctx: dict[str, Any]) -> tuple[str, str]:
    """Try AI generation first, fall back to template."""
    result = generate_email(ctx)
    if result:
        logger.info("AI 生成邮件成功")
        return result
    logger.info("AI 邮件生成不可用，使用模板")
    return _template_email(ctx)


def _template_email(ctx: dict[str, Any]) -> tuple[str, str]:
    """Template-based email as fallback."""
    body: str = ctx["msg"]
    subject: str = f"【纳斯达克数据】{ctx['date']} 涨跌幅 {ctx['pct']:+.2f}%"

    if ctx.get("news"):
        body += "\n────\n📰 今日相关新闻：\n" + "\n".join(f"{i+1}. {h}" for i, h in enumerate(ctx["news"]))
    if ctx.get("drawdown"):
        dd: dict[str, Any] = ctx["drawdown"]
        body += f"\n────\n📉 近3月最大回撤：{dd['max_drawdown_pct']}%（{dd['date']}）"
        subject = f"【异常时段】纳斯达克连跌{ctx['drops']}天，近3月最大回撤 {dd['max_drawdown_pct']}%"
    if ctx.get("recovery"):
        body += f"\n────\n✅ 异常时段结束（连跌{ctx['drops']}天后恢复）"
        subject = f"【纳斯达克数据】异常时段结束 - {ctx['date']} 涨跌幅 {ctx['pct']:+.2f}%"
    if ctx.get("advice"):
        body += "\n" + ctx["advice"]

    return subject, body


def send_email(subject: str, body: str) -> None:
    import smtplib
    from email.mime.text import MIMEText

    cfg: dict[str, Any] = get_email_config()
    if not cfg["user"] or not cfg["password"]:
        logger.warning("邮箱未配置，跳过发送")
        return
    msg: Any = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = cfg["user"]
    msg["To"] = cfg["notify"]
    with smtplib.SMTP_SSL(cfg["server"], cfg["port"]) as server:
        server.login(cfg["user"], cfg["password"])
        server.send_message(msg)


if __name__ == "__main__":
    main()
