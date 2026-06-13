# -*- coding: utf-8 -*-
import os
import csv
import tempfile
from modules.drawdown import calc_max_drawdown_3m


def test_calc_max_drawdown_3m_no_file(monkeypatch) -> None:
    """文件不存在时返回 None"""
    monkeypatch.setattr("modules.drawdown.HISTORY_FILE", "nonexistent.csv")
    result = calc_max_drawdown_3m()
    assert result is None


def test_calc_max_drawdown_3m_less_than_2_rows(monkeypatch) -> None:
    """数据不足2行时返回 None"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("date,close,change,pct,z_score,fetch_time\n")
        f.write("2026-06-01,15000,100,0.67,0.5,2026-06-01\n")
        temp_path = f.name
    try:
        monkeypatch.setattr("modules.drawdown.HISTORY_FILE", temp_path)
        result = calc_max_drawdown_3m()
        assert result is None
    finally:
        os.unlink(temp_path)


def test_calc_max_drawdown_3m_normal(monkeypatch) -> None:
    """正常数据应该计算出回撤"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("date,close,change,pct,z_score,fetch_time\n")
        f.write("2026-05-01,15000,200,1.35,0.8,2026-05-01\n")
        f.write("2026-05-02,14800,-200,-1.33,-1.2,2026-05-02\n")
        f.write("2026-05-03,14500,-300,-2.03,-2.1,2026-05-03\n")
        f.write("2026-05-04,14600,100,0.69,-0.5,2026-05-04\n")
        temp_path = f.name
    try:
        monkeypatch.setattr("modules.drawdown.HISTORY_FILE", temp_path)
        result = calc_max_drawdown_3m()
        assert result is not None
        assert "max_drawdown_pct" in result
        assert "date" in result
        assert result["max_drawdown_pct"] < 0  # 回撤应为负数
    finally:
        os.unlink(temp_path)


def test_calc_max_drawdown_3m_no_drawdown(monkeypatch) -> None:
    """持续上涨时回撤应为 0%"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("date,close,change,pct,z_score,fetch_time\n")
        f.write("2026-05-01,14000,100,0.72,0.5,2026-05-01\n")
        f.write("2026-05-02,14200,200,1.43,1.1,2026-05-02\n")
        f.write("2026-05-03,14500,300,2.11,1.8,2026-05-03\n")
        f.write("2026-05-04,14800,300,2.07,1.9,2026-05-04\n")
        temp_path = f.name
    try:
        monkeypatch.setattr("modules.drawdown.HISTORY_FILE", temp_path)
        result = calc_max_drawdown_3m()
        assert result is not None
        assert result["max_drawdown_pct"] == 0.0
    finally:
        os.unlink(temp_path)
