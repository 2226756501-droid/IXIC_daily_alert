import csv
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

logger: logging.Logger = logging.getLogger(__name__)

HISTORY_FILE: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "history.csv")


def calc_max_drawdown_3m() -> dict[str, Any] | None:
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            rows: list[dict[str, str]] = list(csv.DictReader(f))
    except FileNotFoundError:
        logger.warning("回撤计算：history.csv 不存在")
        return None

    cutoff: datetime = datetime.now(timezone.utc) - timedelta(days=90)
    closes: list[tuple[datetime, float]] = []
    for r in rows:
        try:
            dt: datetime = datetime.strptime(r["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            try:
                dt = datetime.strptime(r["date"], "%m/%d/%Y").replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        if dt >= cutoff:
            closes.append((dt, float(r["close"])))

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
