# -*- coding: utf-8 -*-
import pandas as pd
from modules.visualizer import (
    plot_price_history,
    plot_z_score,
    plot_comparison_chart,
    plot_drawdown_analysis,
    plot_statistics,
)


def _make_df() -> pd.DataFrame:
    return pd.DataFrame({
        "date": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
        "close": [15000.0, 15100.0, 14900.0],
        "pct": [0.5, 0.67, -1.33],
        "z_score": [0.2, 0.8, -2.1],
    })


def test_plot_price_history_returns_figure() -> None:
    fig = plot_price_history(_make_df())
    assert len(fig.data) == 2


def test_plot_price_history_with_multiplier() -> None:
    fig = plot_price_history(_make_df(), multiplier=2.0)
    assert fig.data[1].mode == "markers"


def test_plot_z_score_returns_figure() -> None:
    fig = plot_z_score(_make_df())
    assert len(fig.data) == 1
    assert fig.data[0].type == "bar"


def test_plot_z_score_threshold_changes_with_multiplier() -> None:
    fig_default = plot_z_score(_make_df())
    fig_double = plot_z_score(_make_df(), multiplier=2.0)
    # shapes[2] 是 2σ 红线（shapes[0]=1σ, shapes[1]=-1σ, shapes[2]=+2σ）
    assert fig_default.layout.shapes[2].y0 == 2.0
    assert fig_double.layout.shapes[2].y0 == 4.0


def test_plot_comparison_chart_returns_figure() -> None:
    fig = plot_comparison_chart(_make_df())
    assert len(fig.data) == 2


def test_plot_drawdown_analysis_returns_figure() -> None:
    fig = plot_drawdown_analysis(_make_df())
    assert len(fig.data) == 2


def test_plot_statistics_returns_figure() -> None:
    fig = plot_statistics(_make_df())
    assert len(fig.data) == 4
