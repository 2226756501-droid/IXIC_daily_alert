# -*- coding: utf-8 -*-
from modules.analyzer import (
    calc_z_score,
    describe_z,
    query_similar_events,
    record_abnormal,
    finalize_abnormal,
)


def test_calc_z_score_empty() -> None:
    """空列表应该返回 0"""
    assert calc_z_score([]) == 0.0


def test_calc_z_score_single() -> None:
    """只有1个数据点应该返回 0"""
    assert calc_z_score([1.0]) == 0.0


def test_calc_z_score_all_same() -> None:
    """所有值都一样 → Z=0"""
    assert calc_z_score([2.0, 2.0, 2.0, 2.0, 2.0]) == 0.0


def test_calc_z_score_positive() -> None:
    """最后一天比平均大 → Z 为正"""
    result: float = calc_z_score([1.0, 2.0, 3.0, 4.0, 5.0])
    assert result > 0


def test_calc_z_score_negative() -> None:
    """最后一天比平均小 → Z 为负"""
    result: float = calc_z_score([5.0, 4.0, 3.0, 2.0, 1.0])
    assert result < 0


def test_calc_z_score_only_two() -> None:
    """刚好2个数据点（window < 2），应返回 0"""
    assert calc_z_score([1.0, 2.0]) == 0.0


def test_describe_z_normal() -> None:
    assert describe_z(0.5) == "正常波动"


def test_describe_z_notable() -> None:
    assert describe_z(1.5) == "值得注意"


def test_describe_z_significant() -> None:
    assert describe_z(2.5) == "显著异常"


def test_describe_z_extreme() -> None:
    assert describe_z(3.5) == "极端行情"


def test_describe_z_boundary() -> None:
    """正好在阈值上时归入下一档"""
    assert describe_z(1.0) == "值得注意"  # abs(z) < t1 不成立，进入 t2 范围


def test_describe_z_with_multiplier() -> None:
    """multiplier=2 时阈值翻倍"""
    assert describe_z(1.5, multiplier=2.0) == "正常波动"


def test_query_similar_events_none() -> None:
    """没有匹配事件时返回 None"""
    events: list[dict] = [
        {"lasted_days": 3, "trigger_z": -1.0, "consecutive_drops": 2, "change_pct": -2.0},
    ]
    result = query_similar_events(events, -2.0, 3)
    assert result is None


def test_query_similar_events_match() -> None:
    """有匹配事件时返回统计信息"""
    events: list[dict] = [
        {"lasted_days": 3, "trigger_z": -2.5, "consecutive_drops": 3, "change_pct": -3.0},
        {"lasted_days": 5, "trigger_z": -3.0, "consecutive_drops": 4, "change_pct": -4.0},
    ]
    result = query_similar_events(events, -2.0, 3)
    assert result is not None
    assert result["count"] == 2


def test_record_abnormal() -> None:
    """异常事件记录应该正确添加"""
    memory: dict = {"events": [], "next_id": 1}
    memory = record_abnormal(memory, -2.5, 3, 15000.0, -3.0, "2026-06-01")
    assert len(memory["events"]) == 1
    assert memory["events"][0]["trigger_z"] == -2.5
    assert memory["events"][0]["consecutive_drops"] == 3
    assert memory["events"][0]["lasted_days"] is None


def test_finalize_abnormal() -> None:
    """异常事件完结时应该更新 lasted_days 和 recovery_date"""
    memory: dict = {"events": [], "next_id": 1}
    memory = record_abnormal(memory, -2.5, 3, 15000.0, -3.0, "2026-06-01")
    memory = finalize_abnormal(memory, "2026-06-05", 3)
    assert memory["events"][0]["lasted_days"] == 3
    assert memory["events"][0]["recovery_date"] == "2026-06-05"
