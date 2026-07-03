import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

sys.path.insert(0, os.path.dirname(__file__))

from modules.logger import setup_logging
setup_logging(logging.INFO)

logger: logging.Logger = logging.getLogger("gold")

from modules.gold_fetcher import get_today_gold, init_gold_history
from modules.gold_storage import load_gold_history, load_gold_state, save_gold_state
from modules.gold_types import GoldRecord


def main() -> None:
    import time as _time
    _start: float = _time.time()
    init_gold_history()
    msg, pct, data_date, close, change, open_, high_, low_, volume, cny_price, rate = get_today_gold()
    logger.info(msg)

    if not data_date:
        logger.warning("未获取到有效黄金数据，跳过后续处理")
        return

    records: list[GoldRecord] = load_gold_history()
    fetch_time: str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    new_record: GoldRecord = GoldRecord(data_date, close, change, pct, open_, high_, low_, volume, fetch_time)

    updated: bool = False
    for i, rec in enumerate(records):
        if rec.date == data_date:
            records[i] = new_record
            updated = True
            logger.info("已更新 %s 黄金数据", data_date)
            break

    if not updated:
        records.append(new_record)
        logger.info("已记录 %s 黄金数据", data_date)

    from modules.gold_storage import save_gold_history
    save_gold_history(records)

    state: dict[str, Any] = load_gold_state()
    if pct > 0:
        state["direction"] = "up"
        state["consecutive_rises"] = state.get("consecutive_rises", 0) + 1
        state["consecutive_drops"] = 0
    elif pct < 0:
        state["direction"] = "down"
        state["consecutive_drops"] = state.get("consecutive_drops", 0) + 1
        state["consecutive_rises"] = 0
    else:
        state["direction"] = "flat"
    save_gold_state(state)

    logger.info("黄金价格: $%.2f (¥%.2f) | 涨跌: %+.2f%% | 汇率: %.4f | 连续上涨: %d天 | 连续下跌: %d天",
                close, cny_price, pct, rate, state.get("consecutive_rises", 0), state.get("consecutive_drops", 0))


if __name__ == "__main__":
    import time as _time
    _start_t: float = _time.time()
    try:
        main()
        _dur: float = _time.time() - _start_t
        logger.info("gold.py 运行完成，耗时 %.1fs", _dur)
    except Exception as e:
        logger.exception("gold.py 运行失败: %s", e)
        _dur = _time.time() - _start_t
        logger.error("运行失败，耗时 %.1fs", _dur)
