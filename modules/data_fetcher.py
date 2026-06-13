import csv
import json
import os
from datetime import datetime, timezone
from typing import Any

import requests

HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "history.csv")
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "threshold_config.json")
STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "market_state.json")
MEMORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory.json")


def safe_json(url: str) -> dict[str, Any]:
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {}


def fetch_yahoo_chart(range_str: str = "1d") -> dict[str, Any]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/%5EIXIC?range={range_str}&interval=1d"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    return resp.json()


def load_history() -> list[tuple[str, float, float, float, float, str]]:
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return [
            (
                row["date"],
                float(row["close"]),
                float(row.get("change", "0")),
                float(row.get("pct", "0")),
                float(row.get("z_score", "0")),
                row.get("fetch_time", ""),
            )
            for row in csv.DictReader(f)
        ]


def save_history(records: list[tuple]) -> None:
    with open(HISTORY_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "close", "change", "pct", "z_score", "fetch_time"])
        for r in records:
            fetch_time = r[5] if len(r) > 5 else ""
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
    data = fetch_yahoo_chart("5y")
    results = data["chart"]["result"][0]
    pcts: list[float] = []
    records: list[tuple] = []
    prev: float | None = None
    for ts, c in zip(results["timestamp"], results["indicators"]["quote"][0]["close"]):
        if c is not None:
            date = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
            chg = c - prev if prev else 0
            pct = chg / prev * 100 if prev else 0
            pcts.append(pct)
            from modules.analyzer import calc_z_score
            records.append((date, c, chg, pct, calc_z_score(pcts), ""))
            prev = c
    save_history(records)
    print(f">> 历史数据已初始化，共 {len(records)} 条")


def get_today_data(multiplier: float = 1.0) -> tuple[str, float, str, float, float, float]:
    from modules.analyzer import calc_z_score, describe_z

    data = fetch_yahoo_chart("1d")
    results = data["chart"]["result"][0]
    meta = results["meta"]
    closes = results["indicators"]["quote"][0]["close"]

    latest_close = meta.get("regularMarketPrice")
    if latest_close is None:
        valid = [c for c in closes if c is not None]
        latest_close = valid[-1]
    latest_close = float(latest_close)

    prev_close = float(meta.get("chartPreviousClose", 0))
    if not prev_close:
        valid = [c for c in closes if c is not None]
        prev_close = valid[-2] if len(valid) >= 2 else latest_close

    change = latest_close - prev_close
    pct = change / prev_close * 100
    data_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    direction = "📈 涨" if change >= 0 else "📉 跌"

    records = load_history()
    hist_pcts = [r[3] for r in records]
    window = hist_pcts[-(20 - 1):] + [pct]
    z_score = calc_z_score(window)
    level = describe_z(z_score, multiplier)

    msg = (
        f"纳斯达克指数收于 {latest_close:.2f} 点，"
        f"较前一交易日{direction} {abs(change):.2f} 点，涨跌幅 {pct:+.2f}%。\n"
        f"数据日期 {data_date}，异常度 Z = {z_score:.2f}（{level}）"
    )
    return msg, pct, data_date, latest_close, change, z_score
