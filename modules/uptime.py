import json
import logging
import os
import tempfile
from datetime import datetime, timedelta, timezone
from typing import Any

logger: logging.Logger = logging.getLogger(__name__)

BASE_DIR: str = os.path.dirname(os.path.dirname(__file__))
UPTIME_FILE: str = os.path.join(BASE_DIR, "uptime.json")


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


def load_uptime() -> list[dict[str, Any]]:
    if not os.path.exists(UPTIME_FILE):
        return []
    try:
        with open(UPTIME_FILE) as f:
            return json.load(f)
    except Exception as e:
        logger.warning("读取 uptime 失败: %s", e)
        return []


def save_uptime(records: list[dict[str, Any]]) -> None:
    _atomic_write(UPTIME_FILE, json.dumps(records, indent=2, ensure_ascii=False))


def record_run(success: bool, duration_sec: float | None = None, error: str | None = None) -> None:
    records = load_uptime()
    today: str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    records = [r for r in records if r.get("date") != today]
    records.append({
        "date": today,
        "status": "ok" if success else "error",
        "duration_sec": duration_sec,
        "error": error,
    })
    save_uptime(records)
    logger.info("运行记录已保存: %s - %s", today, "成功" if success else "失败")


def calc_uptime(days: int = 90) -> float:
    records = load_uptime()
    cutoff: datetime = datetime.now(timezone.utc) - timedelta(days=days)
    recent = []
    for r in records:
        try:
            dt = datetime.strptime(r["date"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if dt >= cutoff:
                recent.append(r)
        except ValueError:
            continue
    if not recent:
        return 100.0
    ok: int = sum(1 for r in recent if r["status"] == "ok")
    return round(ok / len(recent) * 100, 1)


def get_recent_runs(n: int = 30) -> list[dict[str, Any]]:
    records = load_uptime()
    return sorted(records, key=lambda r: r["date"], reverse=True)[:n]
