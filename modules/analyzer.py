from typing import Any

LOOKBACK = 20


def calc_z_score(pcts: list[float]) -> float:
    window = pcts[:-1]
    if len(window) < 2:
        return 0.0
    mu = sum(window) / len(window)
    var = sum((x - mu) ** 2 for x in window) / (len(window) - 1)
    std = var ** 0.5
    return 0.0 if std == 0 else (pcts[-1] - mu) / std


def describe_z(z: float, multiplier: float = 1.0) -> str:
    t1, t2, t3 = 1 * multiplier, 2 * multiplier, 3 * multiplier
    if abs(z) < t1:
        return "正常波动"
    if abs(z) < t2:
        return "值得注意"
    if abs(z) < t3:
        return "显著异常"
    return "极端行情"


def query_similar_events(events: list[dict], z: float, drops: int) -> dict | None:
    matched = [
        e for e in events
        if e.get("lasted_days") and e["trigger_z"] <= z and e["consecutive_drops"] >= drops
    ]
    if len(matched) < 2:
        return None
    avg_last = sum(e["lasted_days"] for e in matched) / len(matched)
    avg_change = sum(e["change_pct"] for e in matched) / len(matched)
    return {
        "count": len(matched),
        "avg_lasted_days": round(avg_last, 1),
        "avg_change_pct": round(avg_change, 2),
    }


def build_memory_advice(events: list[dict], z: float, drops: int) -> str:
    ref = query_similar_events(events, z, drops)
    if not ref:
        return ""
    return (
        f"📋 历史参考：过去 {ref['count']} 次类似情况中（Z≤{z:.1f}，连跌≥{drops} 天），"
        f"异常平均持续 {ref['avg_lasted_days']} 天，当日平均涨跌幅 {ref['avg_change_pct']:+.2f}%。"
    )


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
    print(f">> 异常事件 #{memory['next_id'] - 1} 已记录")
    return memory


def finalize_abnormal(memory: dict[str, Any], end_date: str, total_drops: int) -> dict[str, Any]:
    for evt in reversed(memory.get("events", [])):
        if evt.get("lasted_days") is None:
            evt["lasted_days"] = total_drops
            evt["recovery_date"] = end_date
            print(f">> 异常事件 #{evt['id']} 已完结（持续 {total_drops} 天）")
            break
    return memory
