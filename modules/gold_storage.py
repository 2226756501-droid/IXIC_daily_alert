import csv
import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from typing import Any

from modules.gold_types import GoldRecord

logger: logging.Logger = logging.getLogger(__name__)

BASE_DIR: str = os.path.dirname(os.path.dirname(__file__))
GOLD_HISTORY_FILE: str = os.path.join(BASE_DIR, "gold_history.csv")
GOLD_STATE_FILE: str = os.path.join(BASE_DIR, "gold_state.json")


def _atomic_write(path: str, data: str) -> None:
    dirpath: str = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=dirpath, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def load_gold_history() -> list[GoldRecord]:
    if not os.path.exists(GOLD_HISTORY_FILE):
        return []
    with open(GOLD_HISTORY_FILE, "r", encoding="utf-8") as f:
        rows: list[dict[str, str]] = list(csv.DictReader(f))
    result: list[GoldRecord] = []
    for row in rows:
        c = float(row["close"])
        result.append(GoldRecord(
            date=row["date"], close=c,
            change=float(row.get("change", "0")),
            pct=float(row.get("pct", "0")),
            open=float(row.get("open", str(c))),
            high=float(row.get("high", str(c))),
            low=float(row.get("low", str(c))),
            volume=float(row.get("volume", "0")),
            fetch_time=row.get("fetch_time", ""),
        ))
    return result


def save_gold_history(records: list[GoldRecord]) -> None:
    import io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["date", "close", "change", "pct", "open", "high", "low", "volume", "fetch_time"])
    for r in records:
        w.writerow([r.date, f"{r.close:.2f}", f"{r.change:.2f}", f"{r.pct:.2f}",
                   f"{r.open:.2f}", f"{r.high:.2f}", f"{r.low:.2f}", f"{r.volume:.0f}", r.fetch_time])
    _atomic_write(GOLD_HISTORY_FILE, buf.getvalue())


def load_gold_state() -> dict[str, Any]:
    if not os.path.exists(GOLD_STATE_FILE):
        return {"direction": "flat", "consecutive_drops": 0, "consecutive_rises": 0}
    with open(GOLD_STATE_FILE) as f:
        return json.load(f)


def save_gold_state(state: dict[str, Any]) -> None:
    _atomic_write(GOLD_STATE_FILE, json.dumps(state, indent=2))
