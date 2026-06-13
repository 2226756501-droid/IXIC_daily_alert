import os
import sys
from datetime import datetime, timezone
from typing import Any

sys.path.insert(0, os.path.dirname(__file__))

from modules.data_fetcher import (
    init_history, load_history, save_history,
    load_config, load_market_state, save_market_state,
    load_memory, save_memory, get_today_data, Record,
)
from modules.analyzer import record_abnormal, finalize_abnormal, build_memory_advice
from modules.news_fetcher import fetch_nasdaq_news
from modules.config import get_email_config


def main() -> None:
    init_history()
    config: dict[str, Any] = load_config()
    multiplier: float = config["sensitivity_multiplier"]
    msg: str
    pct: float
    data_date: str
    close: float
    change: float
    z_score: float
    msg, pct, data_date, close, change, z_score = get_today_data(multiplier)
    print(msg)

    records: list[Record] = load_history()
    if not records or records[-1][0] != data_date:
        fetch_time: str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        records.append((data_date, close, change, pct, z_score, fetch_time))
        save_history(records)
        print(f">> 已记录 {data_date} 数据")

    state: dict[str, Any] = load_market_state()
    is_down: bool = pct < 0
    body: str = msg
    subject: str = f"【纳斯达克数据】{data_date} 涨跌幅 {pct:+.2f}%"

    if is_down:
        state["consecutive_drops"] = state.get("consecutive_drops", 0) + 1
        drops: int = state["consecutive_drops"]

        if drops == 3 and state.get("state") == "normal":
            state["state"] = "abnormal"
            state["abnormal_since"] = data_date
            mem: dict[str, Any] = load_memory()
            mem = record_abnormal(mem, z_score, drops, close, pct, data_date)
            save_memory(mem)
            news: list[str] = fetch_nasdaq_news()
            if news:
                body += "\n────\n📰 今日相关新闻：\n" + "\n".join(f"{i+1}. {h}" for i, h in enumerate(news))

        elif drops >= 4:
            from modules.drawdown import calc_max_drawdown_3m
            dd: dict[str, Any] | None = calc_max_drawdown_3m()
            if dd:
                state["max_drawdown_3m"] = dd
                body += f"\n────\n📉 近3月最大回撤：{dd['max_drawdown_pct']}%（{dd['date']}）"
                subject = f"【异常时段】纳斯达克连跌{drops}天，近3月最大回撤 {dd['max_drawdown_pct']}%"

    else:
        if state.get("state") == "abnormal":
            drops = state.get("consecutive_drops", 0)
            state["state"] = "normal"
            state["abnormal_since"] = None
            state["consecutive_drops"] = 0
            state["max_drawdown_3m"] = None
            mem = load_memory()
            mem = finalize_abnormal(mem, data_date, drops)
            save_memory(mem)
            body += f"\n────\n✅ 异常时段结束（连跌{drops}天后恢复）"
            subject = f"【纳斯达克数据】异常时段结束 - {data_date} 涨跌幅 {pct:+.2f}%"
        else:
            state["consecutive_drops"] = 0

    save_market_state(state)

    drops = state.get("consecutive_drops", 0)
    if is_down and drops >= 2 and z_score <= -1.5:
        mem = load_memory()
        advice: str = build_memory_advice(mem.get("events", []), z_score, drops)
        if advice:
            body += "\n" + advice

    send_email(subject, body)
    print(">> 邮件已发送")


def send_email(subject: str, body: str) -> None:
    import smtplib
    from email.mime.text import MIMEText

    cfg: dict[str, Any] = get_email_config()
    if not cfg["user"] or not cfg["password"]:
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
