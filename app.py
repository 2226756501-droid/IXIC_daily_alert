import json
import logging
import os
import sys
from datetime import date
from io import StringIO
from typing import Any

sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(level=logging.WARNING)
logger: logging.Logger = logging.getLogger(__name__)

import requests
import streamlit as st
import pandas as pd

from modules.data_fetcher import safe_json
from modules.stats import describe_z
from modules.news_fetcher import fetch_nasdaq_news
from modules.visualizer import (
    plot_candlestick,
    plot_z_score,
    plot_comparison_chart,
    plot_drawdown_analysis,
    plot_statistics,
)
from modules.holidays import is_market_open, next_holiday, next_market_day
from modules import agent_engine

GITHUB_RAW: str = "https://raw.githubusercontent.com/2226756501-droid/IXIC_daily_alert/main"
HISTORY_URL: str = f"{GITHUB_RAW}/history.csv"
STATE_URL: str = f"{GITHUB_RAW}/market_state.json"
MEMORY_URL: str = f"{GITHUB_RAW}/memory.json"
CONFIG_URL: str = f"{GITHUB_RAW}/threshold_config.json"

CACHE_DIR: str = os.path.join(os.path.dirname(__file__), "cache")
CACHE_HISTORY: str = os.path.join(CACHE_DIR, "history.csv")
CACHE_STATE: str = os.path.join(CACHE_DIR, "market_state.json")
CACHE_MEMORY: str = os.path.join(CACHE_DIR, "memory.json")
CACHE_CONFIG: str = os.path.join(CACHE_DIR, "threshold_config.json")

USING_CACHE: dict[str, bool] = {}


def try_write_cache(content: str, path: str) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception:
        pass


def try_write_json_cache(data: dict, path: str) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def fetch_csv_with_cache(url: str, cache_path: str) -> pd.DataFrame | None:
    try:
        resp: requests.Response = requests.get(url, timeout=10)
        resp.raise_for_status()
        content: str = resp.text
        try_write_cache(content, cache_path)
        from io import StringIO
        df: pd.DataFrame = pd.read_csv(StringIO(content))
        df["date"] = pd.to_datetime(df["date"], format="mixed")
        df = df.sort_values("date").reset_index(drop=True)
        return df
    except Exception:
        logger.warning("GitHub raw 加载失败：%s，尝试本地缓存", url)
        if os.path.exists(cache_path):
            USING_CACHE["history"] = True
            df = pd.read_csv(cache_path)
            df["date"] = pd.to_datetime(df["date"], format="mixed")
            df = df.sort_values("date").reset_index(drop=True)
            return df
        return None


def fetch_json_with_cache(url: str, cache_path: str) -> dict[str, Any]:
    try:
        resp: requests.Response = requests.get(url, timeout=10)
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        try_write_json_cache(data, cache_path)
        return data
    except Exception:
        logger.warning("GitHub raw 加载失败：%s，尝试本地缓存", url)
        if os.path.exists(cache_path):
            USING_CACHE["json"] = True
            with open(cache_path, encoding="utf-8") as f:
                return json.load(f)
        return {}

df: pd.DataFrame | None = fetch_csv_with_cache(HISTORY_URL, CACHE_HISTORY)
if df is None:
    st.error("无法加载数据：GitHub 和本地缓存都不可用")
    st.stop()

state: dict[str, Any] = fetch_json_with_cache(STATE_URL, CACHE_STATE)
memory: dict[str, Any] = fetch_json_with_cache(MEMORY_URL, CACHE_MEMORY)
config: dict[str, Any] = fetch_json_with_cache(CONFIG_URL, CACHE_CONFIG)
multiplier: float = config.get("sensitivity_multiplier", 1.0)

if USING_CACHE:
    st.warning("⚠️ GitHub raw 加载失败，使用本地缓存数据（可能不是最新）")

st.set_page_config(page_title="NASDAQ 智能监控", page_icon="📊", layout="wide", initial_sidebar_state="auto")
st.markdown("""
<style>
    .block-container { padding: 1rem 1rem 2rem; }
    @media (max-width: 640px) {
        .block-container { padding: 0.5rem; }
        div[data-testid="column"] { min-width: 50% !important; }
    }
</style>
""", unsafe_allow_html=True)
st.title("📊 NASDAQ 智能监控")
st.caption("数据源：GitHub 实时同步（云端每日自动更新）")

latest: pd.Series = df.iloc[-1]
z: float = latest["z_score"]
level: str = describe_z(z, multiplier)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("当前指数", f"{latest['close']:.2f}", f"{latest['change']:+.2f}")
with col2:
    st.metric("涨跌幅", f"{latest['pct']:+.2f}%", latest["date"].strftime("%m-%d"))
with col3:
    st.metric("异常度 Z", f"{z:.2f}", level)
with col4:
    drops: int = state.get("consecutive_drops", 0)
    st.metric("连续下跌", f"{drops}天", state.get("state", "normal"))

today: date = date.today()
if not is_market_open(today):
    h_date: date | None
    h_name: str
    h_date, h_name = next_holiday(today)
    if h_date == today:
        st.warning(f"🔴 今日美股休市（{h_name}），数据不更新")
    else:
        next_open: date = next_market_day(today)
        st.info(f"💤 今日非交易日，下一个交易日：{next_open}")
else:
    h_date, h_name = next_holiday(today)
    if h_date:
        days_until: int = (h_date - today).days
        st.caption(f"📅 下一个休市日：{h_date}（{h_name}），还有 {days_until} 天")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 行情走势", "📊 统计分析", "📉 回撤分析", "📰 新闻", "⚙️ 异常事件", "🤖 AI 分析"
])

with tab1:
    st.subheader("近 90 日 K 线走势")
    df_90d: pd.DataFrame = df[df["date"] >= df["date"].max() - pd.Timedelta(days=90)]
    st.plotly_chart(plot_candlestick(df_90d, multiplier), use_container_width=True)

    st.subheader("Z-score 异常检测")
    st.plotly_chart(plot_z_score(df_90d, multiplier), use_container_width=True)

    st.subheader("涨跌幅 & Z-score 对比")
    st.plotly_chart(plot_comparison_chart(df_90d, multiplier), use_container_width=True)

with tab2:
    st.subheader("📊 数据统计")
    time_range: str = st.radio(
        "时间范围", ["30天", "90天", "全部"],
        horizontal=True, label_visibility="collapsed",
    )
    df_stats: pd.DataFrame = df
    if time_range == "30天":
        df_stats = df[df["date"] >= df["date"].max() - pd.Timedelta(days=30)]
    elif time_range == "90天":
        df_stats = df[df["date"] >= df["date"].max() - pd.Timedelta(days=90)]
    st.plotly_chart(plot_statistics(df_stats), use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        close_stats: pd.Series = df_stats["close"].describe()
        st.metric("平均收盘", f"{close_stats['mean']:.0f}")
        st.metric("最高收盘", f"{close_stats['max']:.0f}")
        st.metric("最低收盘", f"{close_stats['min']:.0f}")
        st.metric("标准差", f"{close_stats['std']:.0f}")
    with col_b:
        pct_stats: pd.Series = df_stats["pct"].describe()
        st.metric("平均涨跌幅", f"{pct_stats['mean']:.2f}%")
        st.metric("最大涨幅", f"{pct_stats['max']:.2f}%")
        st.metric("最大跌幅", f"{pct_stats['min']:.2f}%")
        st.metric("波动率(σ)", f"{pct_stats['std']:.2f}%")

with tab3:
    st.subheader("📉 回撤分析")
    st.caption("回撤率 = (当前价 - 阶段最高价) / 阶段最高价 × 100%")
    st.plotly_chart(plot_drawdown_analysis(df), use_container_width=True)

with tab4:
    st.subheader("📰 今日 NASDAQ 相关新闻")
    with st.spinner("获取新闻中..."):
        try:
            news: list[str] = fetch_nasdaq_news()
            if news:
                for i, h in enumerate(news, 1):
                    st.write(f"{i}. {h}")
            else:
                st.info("暂无新闻")
        except Exception as e:
            st.warning(f"新闻获取失败：{e}")

with tab5:
    st.subheader("⚙️ 异常事件记录")
    events: list[Any] = memory.get("events", [])
    if events:
        evt_df: pd.DataFrame = pd.DataFrame(events)
        cols: list[str] = ["date", "trigger_z", "consecutive_drops", "close", "change_pct", "lasted_days", "recovery_date"]
        evt_df = evt_df[[c for c in cols if c in evt_df.columns]]
        evt_df = evt_df.fillna("进行中")
        st.dataframe(evt_df, use_container_width=True, hide_index=True)
    else:
        st.info("暂无异常事件记录")

    st.divider()
    st.caption(f"数据范围：{df['date'].min().strftime('%Y-%m-%d')} ~ {df['date'].max().strftime('%Y-%m-%d')}，共 {len(df)} 条记录")

with tab6:
    st.subheader("🤖 AI 分析助手")
    st.caption("基于 DeepSeek V4 Flash，可查询实时数据、历史统计、新闻动态。")

    if not agent_engine.is_available():
        st.info("💡 AI 功能未配置。如需使用，请在 .env 或 Streamlit Secrets 中设置 DEEPSEEK_API_KEY。")

    if "agent_messages" not in st.session_state:
        st.session_state.agent_messages = []

    for msg in st.session_state.agent_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("问任何关于纳斯达克的问题…", disabled=not agent_engine.is_available()):
        st.session_state.agent_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("分析中…"):
                response = agent_engine.chat(prompt, st.session_state.agent_messages[:-1])
            st.markdown(response)
            st.session_state.agent_messages.append({"role": "assistant", "content": response})
