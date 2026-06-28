import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def _thresholds(multiplier: float = 1.0) -> tuple[float, float, float]:
    return (1 * multiplier, 2 * multiplier, 3 * multiplier)


def _threshold(multiplier: float = 1.0) -> float:
    return 2 * multiplier


def plot_candlestick(df: pd.DataFrame, multiplier: float = 1.0) -> go.Figure:
    has_ohlc = all(c in df.columns for c in ["open", "high", "low"])
    fig: go.Figure = go.Figure()
    if has_ohlc:
        fig.add_trace(go.Candlestick(
            x=df["date"], open=df["open"], high=df["high"],
            low=df["low"], close=df["close"],
            name="NASDAQ",
            increasing_line_color="#2ecc71",
            decreasing_line_color="#e74c3c",
        ))
        t2: float = _threshold(multiplier)
        ab_colors: list[str] = ["red" if abs(z) >= t2 else "rgba(0,0,0,0)" for z in df["z_score"]]
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["close"],
            mode="markers", name="异常点",
            marker=dict(color=ab_colors, size=6, symbol="circle"),
            showlegend=False,
        ))
    else:
        fig = plot_price_history(df, multiplier)
        fig.update_layout(xaxis_rangeslider_visible=False)
        return fig
    fig.update_layout(
        template="plotly_white", height=400,
        hovermode="x unified",
        xaxis_title="日期", yaxis_title="价格",
        xaxis_rangeslider_visible=False,
    )
    return fig


def plot_price_history(df: pd.DataFrame, multiplier: float = 1.0) -> go.Figure:
    t: float = _threshold(multiplier)
    fig: go.Figure = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["close"],
        mode="lines", name="收盘价",
        line=dict(color="#1f77b4", width=2),
    ))
    colors: list[str] = ["#e74c3c" if z < -t else "#2ecc71" if z > t else "#1f77b4"
                         for z in df["z_score"]]
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["close"],
        mode="markers", name="异常点",
        marker=dict(color=colors, size=6, symbol="circle"),
        showlegend=False,
    ))
    fig.update_layout(
        template="plotly_white", height=400,
        hovermode="x unified",
        xaxis_title="日期", yaxis_title="收盘价",
    )
    return fig


def plot_z_score(df: pd.DataFrame, multiplier: float = 1.0) -> go.Figure:
    t1, t2, t3 = _thresholds(multiplier)
    fig: go.Figure = go.Figure()
    colors: list[str] = ["#e74c3c" if abs(z) >= t2 else "#3498db" for z in df["z_score"]]
    fig.add_trace(go.Bar(
        x=df["date"], y=df["z_score"],
        marker_color=colors, name="Z-score",
    ))
    fig.add_hline(y=t1, line_dash="dot", line_color="orange", annotation_text=f"+{t1}σ", annotation_font_size=10)
    fig.add_hline(y=-t1, line_dash="dot", line_color="orange", annotation_text=f"-{t1}σ", annotation_font_size=10)
    fig.add_hline(y=t2, line_dash="dash", line_color="red", annotation_text=f"+{t2}σ", annotation_font_size=10)
    fig.add_hline(y=-t2, line_dash="dash", line_color="red", annotation_text=f"-{t2}σ", annotation_font_size=10)
    fig.add_hline(y=t3, line_dash="dash", line_color="darkred", annotation_text=f"+{t3}σ", annotation_font_size=10)
    fig.add_hline(y=-t3, line_dash="dash", line_color="darkred", annotation_text=f"-{t3}σ", annotation_font_size=10)
    fig.update_layout(
        template="plotly_white", height=300,
        hovermode="x unified",
        xaxis_title="日期", yaxis_title="Z-score",
    )
    return fig


def plot_comparison_chart(df: pd.DataFrame, multiplier: float = 1.0) -> go.Figure:
    t1, t2, t3 = _thresholds(multiplier)
    fig: go.Figure = make_subplots(rows=2, cols=1,
                                   subplot_titles=("涨跌幅", "Z-score 异常度"),
                                   vertical_spacing=0.15)
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["pct"], mode="lines+markers",
        name="涨跌幅", line=dict(color="#1f77b4"),
    ), row=1, col=1)
    fig.add_hline(y=0, line_dash="dash", line_color="gray", row=1, col=1)
    fig.add_trace(go.Bar(
        x=df["date"], y=df["z_score"],
        name="Z-score",
        marker_color=["#e74c3c" if abs(z) >= t2 else "#3498db" for z in df["z_score"]],
    ), row=2, col=1)
    for t, c in [(t1, "orange"), (t2, "red"), (t3, "darkred")]:
        fig.add_hline(y=t, line_dash="dot" if t == t1 else "dash", line_color=c, row=2, col=1)
        fig.add_hline(y=-t, line_dash="dot" if t == t1 else "dash", line_color=c, row=2, col=1)
    fig.update_layout(height=500, template="plotly_white", hovermode="x unified")
    return fig


def plot_drawdown_analysis(df: pd.DataFrame) -> go.Figure:
    closes: pd.Series = df["close"].values
    peak: pd.Series = pd.Series(closes).expanding().max()
    drawdown: pd.Series = (closes - peak) / peak * 100
    df = df.copy()
    df["drawdown"] = drawdown

    fig: go.Figure = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["close"],
        mode="lines", name="收盘价",
        line=dict(color="#1f77b4", width=2),
        yaxis="y",
    ))
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["drawdown"],
        mode="lines", name="回撤率 (%)",
        line=dict(color="#e74c3c", width=2),
        fill="tozeroy", fillcolor="rgba(231, 76, 60, 0.15)",
        yaxis="y2",
    ))
    fig.update_layout(
        template="plotly_white", height=400,
        hovermode="x unified",
        xaxis=dict(title="日期"),
        yaxis=dict(title="收盘价", domain=[0.3, 1]),
        yaxis2=dict(title="回撤率 (%)", overlaying="y", side="right", domain=[0, 0.25]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def plot_statistics(df: pd.DataFrame) -> go.Figure:
    fig: go.Figure = make_subplots(
        rows=2, cols=2,
        subplot_titles=("收盘价分布", "涨跌幅分布", "月度收益率", "周度收益率分布"),
        vertical_spacing=0.15, horizontal_spacing=0.1,
    )
    fig.add_trace(go.Histogram(x=df["close"], nbinsx=40, name="收盘价", marker_color="#3498db"), row=1, col=1)
    fig.add_trace(go.Histogram(x=df["pct"], nbinsx=40, name="涨跌幅", marker_color="#2ecc71"), row=1, col=2)

    df["month"] = pd.to_datetime(df["date"]).dt.month
    df["weekday"] = pd.to_datetime(df["date"]).dt.dayofweek
    monthly_avg: pd.Series = df.groupby("month")["pct"].mean()
    fig.add_trace(go.Bar(x=monthly_avg.index, y=monthly_avg.values,
                         name="月均涨跌幅", marker_color="#e74c3c"), row=2, col=1)

    weekdays: list[str] = ["周一", "周二", "周三", "周四", "周五"]
    weekly_data: list[pd.Series] = [df[df["weekday"] == i]["pct"].dropna() for i in range(5)]
    fig.add_trace(go.Box(y=weekly_data, name="周度分布", marker_color="#9b59b6"), row=2, col=2)

    fig.update_layout(height=600, template="plotly_white", showlegend=False)
    fig.update_xaxes(title_text="月份", row=2, col=1, tickmode="array",
                     tickvals=list(range(1, 13)))
    fig.update_xaxes(title_text="", row=2, col=2, tickmode="array",
                     tickvals=list(range(5)), ticktext=weekdays)
    return fig
