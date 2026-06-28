import csv
import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from typing import Any

from modules.types import Record, MarketState, Memory, ThresholdConfig

logger: logging.Logger = logging.getLogger(__name__)

BASE_DIR: str = os.path.dirname(os.path.dirname(__file__))
HISTORY_FILE: str = os.path.join(BASE_DIR, "history.csv")
CONFIG_FILE: str = os.path.join(BASE_DIR, "threshold_config.json")
STATE_FILE: str = os.path.join(BASE_DIR, "market_state.json")
MEMORY_FILE: str = os.path.join(BASE_DIR, "memory.json")
FEEDBACK_FILE: str = os.path.join(BASE_DIR, "feedback.csv")


def _atomic_write(path: str, data: str) -> None:
    dirpath: str = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=dirpath, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
        os.replace(tmp, path)
        logger.debug("原子写入成功: %s", path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def load_history() -> list[Record]:
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        rows: list[dict[str, str]] = list(csv.DictReader(f))
    result: list[Record] = []
    for row in rows:
        c = float(row["close"])
        result.append(Record(
            date=row["date"], close=c,
            change=float(row.get("change", "0")),
            pct=float(row.get("pct", "0")),
            z_score=float(row.get("z_score", "0")),
            open=float(row.get("open", str(c))),
            high=float(row.get("high", str(c))),
            low=float(row.get("low", str(c))),
            volume=float(row.get("volume", "0")),
            fetch_time=row.get("fetch_time", ""),
        ))
    return result


def save_history(records: list[Record]) -> None:
    import io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["date", "close", "change", "pct", "z_score", "open", "high", "low", "volume", "fetch_time"])
    for r in records:
        w.writerow([r.date, f"{r.close:.2f}", f"{r.change:.2f}", f"{r.pct:.2f}", f"{r.z_score:.2f}",
                   f"{r.open:.2f}", f"{r.high:.2f}", f"{r.low:.2f}", f"{r.volume:.0f}", r.fetch_time])
    _atomic_write(HISTORY_FILE, buf.getvalue())


def load_config() -> ThresholdConfig:
    if not os.path.exists(CONFIG_FILE):
        return {"sensitivity_multiplier": 1.0}
    with open(CONFIG_FILE) as f:
        return json.load(f)


def save_config(config: ThresholdConfig) -> None:
    _atomic_write(CONFIG_FILE, json.dumps(config, indent=2))


def load_market_state() -> MarketState:
    if not os.path.exists(STATE_FILE):
        return {"state": "normal", "consecutive_drops": 0, "abnormal_since": None, "max_drawdown_3m": None}
    with open(STATE_FILE) as f:
        return json.load(f)


def save_market_state(state: MarketState) -> None:
    _atomic_write(STATE_FILE, json.dumps(state, indent=2))


def save_feedback(date: str, subject: str, rating: str = "") -> None:
    try:
        has_header: bool = os.path.exists(FEEDBACK_FILE)
        with open(FEEDBACK_FILE, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if not has_header:
                w.writerow(["date", "subject", "rating", "created_at"])
            w.writerow([date, subject, rating, datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")])
    except OSError as e:
        logger.warning("保存反馈失败: %s", e)


def load_feedback() -> list[dict[str, str]]:
    if not os.path.exists(FEEDBACK_FILE):
        return []
    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except Exception as e:
        logger.warning("加载反馈失败: %s", e)
        return []


def load_memory() -> Memory:
    if not os.path.exists(MEMORY_FILE):
        return {"events": [], "next_id": 1}
    with open(MEMORY_FILE) as f:
        return json.load(f)


def save_memory(mem: Memory) -> None:
    _atomic_write(MEMORY_FILE, json.dumps(mem, indent=2))
