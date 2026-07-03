from typing import NamedTuple


class GoldRecord(NamedTuple):
    date: str
    close: float
    change: float
    pct: float
    open: float
    high: float
    low: float
    volume: float
    fetch_time: str
