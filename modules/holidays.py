import logging
from datetime import date, timedelta
from typing import Any

import pandas as pd
import pandas_market_calendars as mcal

logger: logging.Logger = logging.getLogger(__name__)

_calendar = mcal.get_calendar("XNYS")


def _build_holiday_name_map() -> dict[date, str]:
    name_map: dict[date, str] = {}
    try:
        rules = _calendar.regular_holidays.rules
        for rule in rules:
            try:
                for year in range(2024, 2032):
                    dates = rule.dates(
                        pd.Timestamp(f"{year}-01-01"),
                        pd.Timestamp(f"{year}-12-31"),
                    )
                    if isinstance(dates, pd.DatetimeIndex):
                        for d in dates:
                            name_map[d.date()] = rule.name
            except Exception:
                continue
    except Exception as e:
        logger.warning("构建节假日名称映射失败: %s", e)
    return name_map


_HOLIDAY_NAMES: dict[date, str] = _build_holiday_name_map()


def is_market_open(d: date) -> bool:
    try:
        sched = _calendar.schedule(start_date=d, end_date=d)
        return not sched.empty
    except Exception as e:
        logger.warning("查询交易日失败 %s: %s", d, e)
        return d.weekday() < 5


def next_holiday(d: date | None = None) -> tuple[date | None, str]:
    if d is None:
        d = date.today()
    try:
        hdays: tuple = _calendar.holidays().holidays
        future: list[date] = []
        for h in hdays:
            hd: date = pd.Timestamp(h).date()
            if hd >= d:
                future.append(hd)
        future.sort()
        if future:
            hd = future[0]
            return hd, _HOLIDAY_NAMES.get(hd, "休市日")
    except Exception as e:
        logger.warning("查询下一个节假日失败: %s", e)
    return None, ""


def next_market_day(d: date | None = None) -> date:
    if d is None:
        d = date.today()
    start: date = d + timedelta(days=1)
    try:
        valid = _calendar.valid_days(
            start_date=start,
            end_date=start + timedelta(days=365),
        )
        if len(valid) > 0:
            return valid[0].date()
    except Exception as e:
        logger.warning("查询下一个交易日失败: %s", e)
    candidate: date = start
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return candidate
