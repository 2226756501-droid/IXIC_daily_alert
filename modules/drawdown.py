import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger: logging.Logger = logging.getLogger(__name__)

from modules.data_fetcher import load_history


def calc_max_drawdown_3m() -> dict[str, Any] | None:
    records = load_history()
    if len(records) < 2:
        return None

    cutoff: datetime = datetime.now(timezone.utc) - timedelta(days=90)
    closes: list[tuple[datetime, float]] = []
    for r in records:
        try:
            dt: datetime = datetime.strptime(r.date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if dt >= cutoff:
            closes.append((dt, r.close))

    if len(closes) < 2:
        return None

    closes.sort(key=lambda x: x[0])
    peak: float = closes[0][1]
    max_dd: float = 0.0
    max_dd_date: str | None = None
    for dt, c in closes:
        if c > peak:
            peak = c
        dd: float = (c - peak) / peak
        if dd < max_dd:
            max_dd = dd
            max_dd_date = dt.strftime("%Y-%m-%d")

    return {
        "max_drawdown_pct": round(max_dd * 100, 2),
        "date": max_dd_date,
    }
