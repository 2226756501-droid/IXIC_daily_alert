import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timezone, timedelta
import altair as alt
import sys, os

sys.path.insert(0, os.path.dirname(__file__))
from fetch_news import fetch_nasdaq_news

GITHUB_RAW = "https://raw.githubusercontent.com/2226756501-droid/IXIC_daily_alert/main"
HISTORY_URL = f"{GITHUB_RAW}/history.csv"
STATE_URL = f"{GITHUB_RAW}/market_state.json"
MEMORY_URL = f"{GITHUB_RAW}/memory.json"
CONFIG_URL = f"{GITHUB_RAW}/threshold_config.json"
LOOKBACK = 20


def safe_json(url):
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {}


def load_data():
    try:
        df = pd.read_csv(HISTORY_URL)
        df["date"] = pd.to_datetime(df["date"], format="mixed")
        df = df.sort_values("date").reset_index(drop=True)
    except Exception as e:
        st.error(f"数据加载失败：{e}")
        st.stop()
    return df


def calc_z_score(pcts):
    window = pcts[:-1]
    if len(window) < 2:
        return 0.0
    mu = sum(window) / len(window)
    var = sum((x - mu) ** 2 for x in window) / (len(window) - 1)
    std = var ** 0.5
    return 0.0 if std == 0 else (pcts[-1] - mu) / std


def describe_z(z, multiplier=1.0):
    t1, t2, t3 = 1 * multiplier, 2 * multiplier, 3 * multiplier
    if abs(z) < t1:
        return "正常波动"
    if abs(z) < t2:
        return "值得注意"
    if abs(z) < t3:
        return "显著异常"
    return "极端行情"


st.set_page_config(page_title="纳斯达克智能监控", page_icon="📊", layout="wide")

st.title("📊 纳斯达克智能监控系统")
st.caption("数据源：GitHub 实时同步（云端每日自动更新）")

df = load_data()
state = safe_json(STATE_URL)
memory = safe_json(MEMORY_URL)
config = safe_json(CONFIG_URL)
multiplier = config.get("sensitivity_multiplier", 1.0)

latest = df.iloc[-1]
z = latest["z_score"]
level = describe_z(z, multiplier)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("当前指数", f"{latest['close']:.2f}", f"{latest['change']:+.2f}")
with col2:
    st.metric("涨跌幅", f"{latest['pct']:+.2f}%", latest["date"].strftime("%m-%d"))
with col3:
    st.metric("异常度 Z", f"{z:.2f}", level)
with col4:
    drops = state.get("consecutive_drops", 0)
    st.metric("连续下跌", f"{drops}天", state.get("state", "normal"))

st.subheader("📈 近90日 NASDAQ 收盘走势")

col_ch1, col_ch2 = st.columns([3, 2])

with col_ch1:
    df_90d = df[df["date"] >= df["date"].max() - pd.Timedelta(days=90)]
    line = alt.Chart(df_90d).mark_line(point=True).encode(
        x=alt.X("date:T", title="日期"),
        y=alt.Y("close:Q", title="收盘价"),
        tooltip=["date:T", "close:Q", "pct:Q", "z_score:Q"],
    ).properties(height=400)

    abnormal = df_90d[df_90d["z_score"].abs() >= 2]
    if not abnormal.empty:
        pts = alt.Chart(abnormal).mark_point(size=120, color="red", shape="diamond").encode(
            x="date:T", y="close:Q", tooltip=["date:T", "close:Q", "z_score:Q"]
        )
        line += pts

    st.altair_chart(line, use_container_width=True)

with col_ch2:
    df_z = df_90d.copy()
    df_z["mark"] = df_z["z_score"].apply(lambda x: "异常" if abs(x) >= 2 else "正常")
    bars = alt.Chart(df_z).mark_bar().encode(
        x="date:T",
        y="z_score:Q",
        color=alt.Color("mark:N", scale=alt.Scale(domain=["异常", "正常"], range=["#e74c3c", "#3498db"])),
    ).properties(height=400, title="Z-score 异常检测")
    rule = alt.Chart(pd.DataFrame({"y": [2, -2]})).mark_rule(color="red", strokeDash=[5, 5]).encode(y="y:Q")
    st.altair_chart(bars + rule, use_container_width=True)

st.subheader("📋 异常事件记录")
events = memory.get("events", [])
if events:
    evt_df = pd.DataFrame(events)
    cols = ["date", "trigger_z", "consecutive_drops", "close", "change_pct", "lasted_days", "recovery_date"]
    evt_df = evt_df[[c for c in cols if c in evt_df.columns]]
    evt_df = evt_df.fillna("进行中")
    st.dataframe(evt_df, use_container_width=True, hide_index=True)
else:
    st.info("暂无异常事件记录")

st.subheader("📰 今日相关新闻")
with st.spinner("获取新闻中..."):
    try:
        news = fetch_nasdaq_news()
        if news:
            for i, h in enumerate(news, 1):
                st.write(f"{i}. {h}")
        else:
            st.info("暂无新闻")
    except Exception as e:
        st.warning(f"新闻获取失败：{e}")

st.divider()
f1, f2, f3 = st.columns(3)
with f1:
    st.caption(f"历史数据共 {len(df)} 条")
with f2:
    st.caption(f"阈值倍率：{multiplier}")
with f3:
    st.caption(f"最新：{latest['date'].strftime('%Y-%m-%d')}")
