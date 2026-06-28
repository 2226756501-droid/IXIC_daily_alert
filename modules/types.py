from typing import Any, NamedTuple, NotRequired, TypedDict


class Record(NamedTuple):
    date: str
    close: float
    change: float
    pct: float
    z_score: float
    open: float
    high: float
    low: float
    volume: float
    fetch_time: str


class EmailConfig(TypedDict):
    server: str
    port: int
    user: str
    password: str
    notify: str


class DrawdownInfo(TypedDict):
    max_drawdown_pct: float
    date: str | None


class MarketState(TypedDict, total=False):
    state: str
    consecutive_drops: int
    abnormal_since: str | None
    max_drawdown_3m: DrawdownInfo | None


class TodayData(TypedDict):
    msg: str
    pct: float
    date: str
    close: float
    change: float
    z_score: float
    open: float
    high: float
    low: float
    volume: float


class MemoryEvent(TypedDict, total=False):
    id: int
    date: str
    trigger_z: float
    consecutive_drops: int
    close: float
    change_pct: float
    lasted_days: int | None
    recovery_date: str | None


class Memory(TypedDict, total=False):
    events: list[MemoryEvent]
    next_id: int


class ThresholdConfig(TypedDict):
    sensitivity_multiplier: float


class EmailContext(TypedDict, total=False):
    msg: str
    date: str
    pct: float
    close: float
    change: float
    z_score: float
    adjusted_z: float
    regime: str
    regime_note: str
    vol_ratio: float
    is_down: bool
    state: str
    drops: int
    news: list[str] | None
    drawdown: DrawdownInfo | None
    recovery: bool
    advice: str | None
