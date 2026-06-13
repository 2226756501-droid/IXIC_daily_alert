import csv
from datetime import datetime, timedelta, timezone

HISTORY_FILE = "history.csv"


def calc_max_drawdown_3m():
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        return None

    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    closes = []
    for r in rows:
        try:
            dt = datetime.strptime(r["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
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
    peak = closes[0][1]
    max_dd = 0.0
    max_dd_date = None
    for dt, c in closes:
        if c > peak:
            peak = c
        dd = (c - peak) / peak
        if dd < max_dd:
            max_dd = dd
            max_dd_date = dt.strftime("%Y-%m-%d")

    return {
        "max_drawdown_pct": round(max_dd * 100, 2),
        "date": max_dd_date,
    }
