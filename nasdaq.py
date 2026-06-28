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
from modules.stats import build_memory_advice, calc_volatility_regime, calc_volume_ratio, adjust_z_by_regime
from modules.news_fetcher import fetch_nasdaq_news
from modules.mailer import build_email, send_email
from modules.data_fetcher import save_feedback, load_feedback

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
    state: dict[str, Any] = load_market_state()
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

    # Volatility regime & volume
    hist_pcts: list[float] = [r.pct for r in records]
    hist_volumes: list[float] = [r.volume for r in records if r.volume > 0]
    regime: str = calc_volatility_regime(hist_pcts + [pct])
    vol_ratio: float = calc_volume_ratio(volume, hist_volumes)
    adjusted_z, regime_note = adjust_z_by_regime(z_score, regime)

    # Collect context for AI email generation
    abnormal_state: str = state.get("state", "normal")
    ctx: dict[str, Any] = {
        "msg": msg, "date": data_date, "pct": pct,
        "close": close, "change": change, "z_score": z_score,
        "adjusted_z": round(adjusted_z, 2), "regime": regime,
        "regime_note": regime_note, "vol_ratio": round(vol_ratio, 2),
        "is_down": is_down, "state": abnormal_state,
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
    main()
