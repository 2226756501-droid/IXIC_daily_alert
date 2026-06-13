# -*- coding: utf-8 -*-
from datetime import date
from modules.holidays import is_market_open, next_holiday, next_market_day


def test_is_market_open_weekday() -> None:
    """普通工作日应该开市"""
    d: date = date(2026, 6, 15)  # Monday
    assert is_market_open(d) is True


def test_is_market_open_weekend() -> None:
    """周末应该休市"""
    d: date = date(2026, 6, 13)  # Saturday
    assert is_market_open(d) is False


def test_is_market_open_holiday() -> None:
    """节假日应该休市"""
    d: date = date(2026, 12, 25)  # Christmas
    assert is_market_open(d) is False


def test_next_holiday_exists() -> None:
    """应该能找到下一个节假日"""
    d: date = date(2026, 12, 20)
    h_date, h_name = next_holiday(d)
    assert h_date is not None
    assert h_name != ""


def test_next_holiday_after_last() -> None:
    """超过最后一个节假日应该返回 None"""
    d: date = date(2028, 1, 1)
    h_date, h_name = next_holiday(d)
    assert h_date is None


def test_next_market_day_after_weekend() -> None:
    """周末后的下一个交易日应该是周一"""
    d: date = date(2026, 6, 13)  # Saturday
    next_day: date = next_market_day(d)
    assert next_day.weekday() == 0  # Monday
