import logging
from typing import Any

logger: logging.Logger = logging.getLogger(__name__)

LOOKBACK: int = 20


def calc_z_score(pcts: list[float]) -> float:
    data: list[float] = pcts[-LOOKBACK:]
    window: list[float] = data[:-1]
    if len(window) < 2:
        return 0.0
    mu: float = sum(window) / len(window)
    var: float = sum((x - mu) ** 2 for x in window) / (len(window) - 1)
    std: float = var ** 0.5
    return 0.0 if std == 0 else (data[-1] - mu) / std


def describe_z(z: float, multiplier: float = 1.0) -> str:
    t1: float = 1 * multiplier
    t2: float = 2 * multiplier
    t3: float = 3 * multiplier
    if abs(z) < t1:
        return "正常波动"
    if abs(z) < t2:
        return "值得注意"
    if abs(z) < t3:
        return "显著异常"
    return "极端行情"


def query_similar_events(events: list[dict[str, Any]], z: float, drops: int) -> dict[str, Any] | None:
    matched: list[dict[str, Any]] = [
        e for e in events
        if e.get("lasted_days") and e["trigger_z"] <= z and e["consecutive_drops"] >= drops
    ]
    if len(matched) < 2:
        return None
    avg_last: float = sum(e["lasted_days"] for e in matched) / len(matched)
    avg_change: float = sum(e["change_pct"] for e in matched) / len(matched)
    return {
        "count": len(matched),
        "avg_lasted_days": round(avg_last, 1),
        "avg_change_pct": round(avg_change, 2),
    }


VOLATILITY_WINDOW: int = 60
VOLUME_WINDOW: int = 20


def calc_volatility_regime(pcts: list[float]) -> str:
    """Classify volatility: 'low' / 'normal' / 'high' based on 60-day vs full std."""
    if len(pcts) < VOLATILITY_WINDOW:
        return "normal"
    recent: list[float] = pcts[-VOLATILITY_WINDOW:]
    recent_mu: float = sum(recent) / len(recent)
    recent_var: float = sum((x - recent_mu) ** 2 for x in recent) / (len(recent) - 1)
    recent_std: float = recent_var ** 0.5
    full_mu: float = sum(pcts) / len(pcts)
    full_var: float = sum((x - full_mu) ** 2 for x in pcts) / (len(pcts) - 1)
    full_std: float = full_var ** 0.5
    ratio: float = recent_std / full_std if full_std > 1e-8 else 1.0
    if ratio < 0.7:
        return "low"
    if ratio > 1.5:
        return "high"
    return "normal"


def calc_volume_ratio(volume: float, volumes: list[float]) -> float:
    """Volume / 20-day avg. >1.5 = significant spike."""
    window: list[float] = [v for v in (volumes[-VOLUME_WINDOW:] if len(volumes) >= VOLUME_WINDOW else volumes) if v > 0]
    if len(window) < 2:
        return 1.0
    avg: float = sum(window) / len(window)
    return volume / avg if avg > 0 else 1.0


def adjust_z_by_regime(z: float, regime: str) -> tuple[float, str]:
    """Adjust Z-score interpretation based on volatility regime."""
    shifts: dict[str, float] = {"low": 0.5, "high": -0.5}
    shift: float = shifts.get(regime, 0.0)
    adjusted: float = z + shift
    note: str = ""
    if regime == "low":
        note = "（低波动环境，同等 Z 值更值得警惕）"
    elif regime == "high":
        note = "（高波动环境，同等 Z 值需结合量能判断）"
    return adjusted, note


def build_memory_advice(events: list[dict[str, Any]], z: float, drops: int) -> str:
    ref: dict[str, Any] | None = query_similar_events(events, z, drops)
    if not ref:
        return ""
    return (
        f"历史参考：过去 {ref['count']} 次类似情况中（Z≤{z:.1f}，连跌≥{drops} 天），"
        f"异常平均持续 {ref['avg_lasted_days']} 天，当日平均涨跌幅 {ref['avg_change_pct']:+.2f}%。"
    )
