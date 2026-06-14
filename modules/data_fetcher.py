import csv
import json
import os
from datetime import datetime, timezone
from typing import Any

import requests

HISTORY_FILE: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "history.csv")
CONFIG_FILE: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "threshold_config.json")
STATE_FILE: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "market_state.json")
MEMORY_FILE: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory.json")

Record = tuple[str, float, float, float, float, str]


def safe_json(url: str) -> dict[str, Any]:
    try:
        resp: requests.Response = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {}


def fetch_yahoo_chart(range_str: str = "1d") -> dict[str, Any]:
    url: str = f"https://query1.finance.yahoo.com/v8/finance/chart/%5EIXIC?range={range_str}&interval=1d"
    try:
        resp: requests.Response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"!! Yahoo Finance API 请求失败：{e}")
        return {}


def load_history() -> list[Record]:
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        rows: list[dict[str, str]] = list(csv.DictReader(f))
    result: list[Record] = []
    for row in rows:
        result.append((
            row["date"],
            float(row["close"]),
            float(row.get("change", "0")),
            float(row.get("pct", "0")),
            float(row.get("z_score", "0")),
            row.get("fetch_time", ""),
        ))
    return result


def save_history(records: list[Record]) -> None:
    with open(HISTORY_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "close", "change", "pct", "z_score", "fetch_time"])
        for r in records:
            fetch_time: str = r[5] if len(r) > 5 else ""
            w.writerow([r[0], f"{r[1]:.2f}", f"{r[2]:.2f}", f"{r[3]:.2f}", f"{r[4]:.2f}", fetch_time])


def load_config() -> dict[str, Any]:
    if not os.path.exists(CONFIG_FILE):
        return {"sensitivity_multiplier": 1.0}
    with open(CONFIG_FILE) as f:
        return json.load(f)


def load_market_state() -> dict[str, Any]:
    if not os.path.exists(STATE_FILE):
        return {"state": "normal", "consecutive_drops": 0, "abnormal_since": None, "max_drawdown_3m": None}
    with open(STATE_FILE) as f:
        return json.load(f)


def save_market_state(state: dict[str, Any]) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def load_memory() -> dict[str, Any]:
    if not os.path.exists(MEMORY_FILE):
        return {"events": [], "next_id": 1}
    with open(MEMORY_FILE) as f:
        return json.load(f)


def save_memory(mem: dict[str, Any]) -> None:
    with open(MEMORY_FILE, "w") as f:
        json.dump(mem, f, indent=2)


def init_history() -> None:
    if load_history():
        return
    data: dict[str, Any] = fetch_yahoo_chart("5y")
    if not data.get("chart", {}).get("result"):
        print("!! 获取历史数据失败，跳过初始化")
        return
    results: dict[str, Any] = data["chart"]["result"][0]
    pcts: list[float] = []
    records: list[Record] = []
    prev: float | None = None
    timestamps: list[int] = results["timestamp"]
    quotes: list[float | None] = results["indicators"]["quote"][0]["close"]
    for ts, c in zip(timestamps, quotes):
        if c is not None:
            date: str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
            chg: float = c - prev if prev else 0
            pct: float = chg / prev * 100 if prev else 0
            pcts.append(pct)
            from modules.analyzer import calc_z_score
            records.append((date, c, chg, pct, calc_z_score(pcts), ""))
            prev = c
    save_history(records)
    print(f">> 历史数据已初始化，共 {len(records)} 条")


def get_today_data(multiplier: float = 1.0) -> tuple[str, float, str, float, float, float]:
    from modules.analyzer import calc_z_score, describe_z

    data: dict[str, Any] = fetch_yahoo_chart("1d")
    if not data.get("chart", {}).get("result"):
        print("!! 获取今日数据失败，使用本地缓存")
        records_cache: list[Record] = load_history()
        if records_cache:
            last: Record = records_cache[-1]
            return (f"使用缓存数据：{last[0]} 收盘 {last[1]:.2f}", last[3], last[0], last[1], last[2], last[4])
        return ("无法获取数据", 0.0, "", 0.0, 0.0, 0.0)
    results: dict[str, Any] = data["chart"]["result"][0]
    meta: dict[str, Any] = results["meta"]
    closes: list[float | None] = results["indicators"]["quote"][0]["close"]

    latest_close: float | None = meta.get("regularMarketPrice")
    if latest_close is None:
        valid: list[float] = [c for c in closes if c is not None]
        latest_close = valid[-1]
    latest_close = float(latest_close)

    prev_close: float = float(meta.get("chartPreviousClose", 0))
    if not prev_close:
        valid = [c for c in closes if c is not None]
        prev_close = valid[-2] if len(valid) >= 2 else latest_close

    change: float = latest_close - prev_close
    pct: float = change / prev_close * 100
    data_date: str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    direction: str = "📈 涨" if change >= 0 else "📉 跌"

    records: list[Record] = load_history()
    hist_pcts: list[float] = [r[3] for r in records]
    z_score: float = calc_z_score(hist_pcts + [pct])
    level: str = describe_z(z_score, multiplier)

    msg: str = (
        f"纳斯达克指数收于 {latest_close:.2f} 点，"
        f"较前一交易日{direction} {abs(change):.2f} 点，涨跌幅 {pct:+.2f}%。\n"
        f"数据日期 {data_date}，异常度 Z = {z_score:.2f}（{level}）"
    )
    return msg, pct, data_date, latest_close, change, z_score
