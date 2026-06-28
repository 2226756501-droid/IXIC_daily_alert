import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

sys.path.insert(0, os.path.dirname(__file__))

from modules.logger import setup_logging
setup_logging(logging.INFO)

logger: logging.Logger = logging.getLogger("nasdaq")

from modules.data_fetcher import init_history, get_today_data
from modules.storage import (
    load_history, save_history, load_config,
    load_market_state, save_market_state,
    load_memory, save_memory, save_feedback,
)
from modules.analyzer import record_abnormal
from modules.stats import (
    build_memory_advice, calc_volatility_regime,
    calc_volume_ratio, adjust_z_by_regime,
)
from modules.news_fetcher import fetch_nasdaq_news
from modules.mailer import build_email, send_email
from modules.types import Record, MarketState, EmailContext

ABNORMAL_DRAWDOWN_DROPS: int = 4
ABNORMAL_TRIGGER_DROPS: int = 3
ADVICE_TRIGGER_DROPS: int = 2
ADVICE_TRIGGER_Z: float = -1.5


def calc_consecutive_drops(records: list[Record]) -> int:
    count: int = 0
    for rec in reversed(records):
        if rec.pct < 0:
            count += 1
        else:
            break
    return count


def main() -> None:
    init_history()
    config: dict[str, Any] = load_config()
    multiplier: float = config["sensitivity_multiplier"]
    msg, pct, data_date, close, change, z_score, open_, high_, low_, volume = get_today_data(multiplier)
    logger.info(msg)

    if not data_date:
        logger.warning("未获取到有效数据，跳过后续处理")
        return

    records: list[Record] = load_history()
    fetch_time: str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    new_record: Record = Record(data_date, close, change, pct, z_score, open_, high_, low_, volume, fetch_time)

    updated: bool = False
    for i, rec in enumerate(records):
        if rec.date == data_date:
            records[i] = new_record
            updated = True
            logger.info("已更新 %s 数据", data_date)
            break

    if not updated:
        records.append(new_record)
        logger.info("已记录 %s 数据", data_date)

    drops: int = calc_consecutive_drops(records)
    is_down: bool = pct < 0
    state: MarketState = load_market_state()
    was_abnormal: bool = state.get("state") == "abnormal"

    if drops >= ABNORMAL_DRAWDOWN_DROPS:
        from modules.drawdown import calc_max_drawdown_3m
        dd: dict[str, Any] | None = calc_max_drawdown_3m()
        if dd:
            state["max_drawdown_3m"] = dd

    abnormal_news: list[str] | None = None
    if is_down and drops >= ABNORMAL_TRIGGER_DROPS and not was_abnormal:
        state["state"] = "abnormal"
        state["abnormal_since"] = data_date
        mem: dict[str, Any] = load_memory()
        mem = record_abnormal(mem, z_score, drops, close, pct, data_date)
        save_memory(mem)
        abnormal_news = fetch_nasdaq_news()
    elif not is_down and was_abnormal:
        state["state"] = "normal"
        state["abnormal_since"] = None
        state["max_drawdown_3m"] = None

    state["consecutive_drops"] = drops

    save_market_state(state)
    logger.info("市场状态已保存: consecutive_drops=%s, state=%s", drops, state.get("state"))

    save_history(records)

    hist_pcts: list[float] = [r.pct for r in records]
    hist_volumes: list[float] = [r.volume for r in records if r.volume > 0]
    regime: str = calc_volatility_regime(hist_pcts + [pct])
    vol_ratio: float = calc_volume_ratio(volume, hist_volumes)
    adjusted_z, regime_note = adjust_z_by_regime(z_score, regime)

    ctx: EmailContext = {
        "msg": msg, "date": data_date, "pct": pct,
        "close": close, "change": change, "z_score": z_score,
        "adjusted_z": round(adjusted_z, 2), "regime": regime,
        "regime_note": regime_note, "vol_ratio": round(vol_ratio, 2),
        "is_down": is_down, "state": str(state.get("state", "normal")),
        "drops": drops, "news": abnormal_news,
        "drawdown": state.get("max_drawdown_3m"),
        "recovery": not is_down and was_abnormal,
        "advice": None,
    }

    if is_down and drops >= ADVICE_TRIGGER_DROPS and z_score <= ADVICE_TRIGGER_Z:
        mem = load_memory()
        advice: str = build_memory_advice(mem.get("events", []), z_score, drops)
        if advice:
            ctx["advice"] = advice

    subject, body = build_email(ctx)
    body += "\n\n────\n💬 这封邮件对你有帮助吗？回复 1=满意 2=不满意"
    save_feedback(data_date, subject)
    send_email(subject, body)
    logger.info("邮件已发送")


if __name__ == "__main__":
    try:
        main()
        health = {"status": "ok", "last_success": datetime.now(timezone.utc).isoformat(), "last_error": None, "error_message": None}
    except Exception as e:
        logger.exception("nasdaq.py 运行失败: %s", e)
        health = {"status": "error", "last_success": None, "last_error": datetime.now(timezone.utc).isoformat(), "error_message": str(e)}
        try:
            from modules.mailer import send_email
            send_email("⚠️ NASDAQ 日报运行失败", f"错误信息：{e}\n\n请检查 GitHub Actions 日志。")
        except Exception:
            logger.exception("发送告警邮件失败")
    finally:
        import json, os
        health_file = os.path.join(os.path.dirname(__file__), "health.json")
        with open(health_file, "w") as f:
            json.dump(health, f, indent=2)
