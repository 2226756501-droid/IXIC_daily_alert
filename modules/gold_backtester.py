import logging
from typing import Any

from modules.stats import calc_z_score
from modules.gold_storage import load_gold_history
from modules.gold_types import GoldRecord

logger: logging.Logger = logging.getLogger(__name__)

FORECAST_DAYS: int = 10
SIGNIFICANT_DROP: float = -2.0
MULTIPLIER_VALUES: list[float] = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]


def _calc_future_max_drawdown(records: list[GoldRecord], start_idx: int) -> float:
    peak: float = records[start_idx].close
    max_dd: float = 0.0
    for i in range(start_idx, min(start_idx + FORECAST_DAYS + 1, len(records))):
        c: float = records[i].close
        if c > peak:
            peak = c
        dd: float = (c - peak) / peak * 100
        if dd < max_dd:
            max_dd = dd
    return max_dd


def run_gold_backtest(
    records: list[GoldRecord] | None = None,
    multipliers: list[float] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if records is None:
        records = load_gold_history()
    if multipliers is None:
        multipliers = MULTIPLIER_VALUES
    if len(records) < 30:
        return [], []

    pcts: list[float] = [r.pct for r in records]
    results: list[dict[str, Any]] = []
    events_detail: list[dict[str, Any]] = []

    for mult in multipliers:
        tp = fp = fn = tn = 0
        alerts = 0
        correct_alerts = 0
        detail_events: list[dict[str, Any]] = []

        for i in range(20, len(records)):
            window_pcts: list[float] = pcts[:i + 1]
            z: float = calc_z_score(window_pcts)
            threshold: float = 2.0 * mult

            if abs(z) >= threshold:
                alerts += 1
                future_dd: float = _calc_future_max_drawdown(records, i)
                is_correct: bool = future_dd <= SIGNIFICANT_DROP
                if is_correct:
                    tp += 1
                    correct_alerts += 1
                else:
                    fp += 1
                detail_events.append({
                    "date": records[i].date,
                    "multiplier": mult,
                    "z_score": round(z, 2),
                    "threshold": round(threshold, 1),
                    "close": records[i].close,
                    "pct": records[i].pct,
                    "future_max_dd": round(future_dd, 2),
                    "is_correct": is_correct,
                })

        for i in range(20, len(records)):
            window_pcts = pcts[:i + 1]
            z = calc_z_score(window_pcts)
            threshold = 2.0 * mult
            future_dd = _calc_future_max_drawdown(records, i)
            actually_bad: bool = future_dd <= SIGNIFICANT_DROP
            alert_triggered: bool = abs(z) >= threshold
            if not alert_triggered and not actually_bad:
                tn += 1
            elif not alert_triggered and actually_bad:
                fn += 1

        precision: float = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall: float = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1: float = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        results.append({
            "multiplier": mult,
            "threshold_2sigma": round(threshold, 1),
            "total_alerts": alerts,
            "correct_alerts": correct_alerts,
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1_score": round(f1, 3),
            "true_positive": tp,
            "false_positive": fp,
            "true_negative": tn,
            "false_negative": fn,
            "alert_rate": round(alerts / (len(records) - 20) * 100, 1),
        })

        if mult == 1.0:
            events_detail = detail_events

    return results, events_detail


def get_optimal_multiplier(results: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not results:
        return None
    best: dict[str, Any] = max(results, key=lambda r: r["f1_score"])
    return best
