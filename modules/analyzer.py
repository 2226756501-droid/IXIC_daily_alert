import logging
from typing import Any

from modules.stats import calc_z_score, describe_z, query_similar_events, build_memory_advice

logger: logging.Logger = logging.getLogger(__name__)


def record_abnormal(
    memory: dict[str, Any],
    z: float,
    drops: int,
    close: float,
    pct: float,
    date: str,
) -> dict[str, Any]:
    memory.setdefault("events", []).append({
        "id": memory["next_id"],
        "date": date,
        "trigger_z": round(z, 2),
        "consecutive_drops": drops,
        "close": round(close, 2),
        "change_pct": round(pct, 2),
        "lasted_days": None,
        "recovery_date": None,
    })
    memory["next_id"] += 1
    logger.info("异常事件 #%s 已记录", memory["next_id"] - 1)
    return memory


def finalize_abnormal(memory: dict[str, Any], end_date: str, total_drops: int) -> dict[str, Any]:
    for evt in reversed(memory.get("events", [])):
        if evt.get("lasted_days") is None:
            evt["lasted_days"] = total_drops
            evt["recovery_date"] = end_date
            logger.info("异常事件 #%s 已完结（持续 %s 天）", evt["id"], total_drops)
            break
    return memory
