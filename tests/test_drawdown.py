from unittest.mock import patch

from modules.drawdown import calc_max_drawdown_3m
from modules.data_fetcher import Record


def test_calc_max_drawdown_3m_no_file() -> None:
    with patch("modules.drawdown.load_history", return_value=[]):
        result = calc_max_drawdown_3m()
        assert result is None


def test_calc_max_drawdown_3m_less_than_2_rows() -> None:
    records = [Record("2026-05-01", 15000.0, 100.0, 0.67, 0.5, 15000.0, 15100.0, 14900.0, 1000000.0, "")]
    with patch("modules.drawdown.load_history", return_value=records):
        result = calc_max_drawdown_3m()
        assert result is None


def test_calc_max_drawdown_3m_normal() -> None:
    records = [
        Record("2026-05-01", 15000.0, 200.0, 1.35, 0.8, 15000.0, 15100.0, 14900.0, 1000000.0, ""),
        Record("2026-05-02", 14800.0, -200.0, -1.33, -1.2, 14800.0, 14900.0, 14700.0, 1100000.0, ""),
        Record("2026-05-03", 14500.0, -300.0, -2.03, -2.1, 14500.0, 14600.0, 14400.0, 1200000.0, ""),
        Record("2026-05-04", 14600.0, 100.0, 0.69, -0.5, 14600.0, 14700.0, 14500.0, 900000.0, ""),
    ]
    with patch("modules.drawdown.load_history", return_value=records):
        result = calc_max_drawdown_3m()
        assert result is not None
        assert "max_drawdown_pct" in result
        assert "date" in result
        assert result["max_drawdown_pct"] < 0


def test_calc_max_drawdown_3m_no_drawdown() -> None:
    records = [
        Record("2026-05-01", 14000.0, 100.0, 0.72, 0.5, 14000.0, 14100.0, 13900.0, 1000000.0, ""),
        Record("2026-05-02", 14200.0, 200.0, 1.43, 1.1, 14200.0, 14300.0, 14100.0, 1100000.0, ""),
        Record("2026-05-03", 14500.0, 300.0, 2.11, 1.8, 14500.0, 14600.0, 14400.0, 1200000.0, ""),
        Record("2026-05-04", 14800.0, 300.0, 2.07, 1.9, 14800.0, 14900.0, 14700.0, 900000.0, ""),
    ]
    with patch("modules.drawdown.load_history", return_value=records):
        result = calc_max_drawdown_3m()
        assert result is not None
        assert result["max_drawdown_pct"] == 0.0
