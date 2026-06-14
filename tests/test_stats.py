# -*- coding: utf-8 -*-
from modules.stats import (
    calc_z_score,
    describe_z,
    query_similar_events,
    build_memory_advice,
    LOOKBACK,
)


def test_calc_z_score_lookback() -> None:
    history: list[float] = [float(i) for i in range(LOOKBACK)]
    assert calc_z_score(history + [LOOKBACK + 5]) > 0


def test_calc_z_score_positive_negative() -> None:
    assert calc_z_score([1.0, 2.0, 3.0, 4.0, 5.0]) > 0
    assert calc_z_score([5.0, 4.0, 3.0, 2.0, 1.0]) < 0


def test_build_memory_advice_no_events() -> None:
    assert build_memory_advice([], -2.0, 3) == ""


def test_build_memory_advice_with_events() -> None:
    events: list[dict] = [
        {"lasted_days": 3, "trigger_z": -2.5, "consecutive_drops": 3, "change_pct": -3.0},
        {"lasted_days": 5, "trigger_z": -3.0, "consecutive_drops": 4, "change_pct": -4.0},
    ]
    result: str = build_memory_advice(events, -2.0, 3)
    assert "历史参考" in result
    assert "2 次" in result
