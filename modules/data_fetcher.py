import csv
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

import requests

from modules.stats import calc_z_score, describe_z

logger: logging.Logger = logging.getLogger(__name__)

HISTORY_FILE: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "history.csv")
CONFIG_FILE: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "threshold_config.json")
STATE_FILE: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "market_state.json")
MEMORY_FILE: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory.json")
FEEDBACK_FILE: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "feedback.csv")

Record = tuple[str, float, float, float, float, float, float, float, float, str]


def _request_with_retry(url: str, headers: dict[str, str], max_retries: int = 3) -> requests.Response | None:
    for attempt in range(max_retries):
        try:
            resp: requests.Response = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            if attempt < max_retries - 1:
                wait: float = 2.0 ** attempt
                logger.warning("请求失败(第%d次)，%ds后重试: %s", attempt + 1, wait, e)
                time.sleep(wait)
            else:
                logger.warning("请求失败，已重试%d次: %s", max_retries, e)
                return None
    return None


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
    resp: requests.Response | None = _request_with_retry(url, {"User-Agent": "Mozilla/5.0"})
    if resp is None:
        return {}
    try:
        return resp.json()
    except Exception as e:
        logger.warning("Yahoo Finance API 解析失败: %s", e)
        return {}


def load_history() -> list[Record]:
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        rows: list[dict[str, str]] = list(csv.DictReader(f))
    result: list[Record] = []
    for row in rows:
        c = float(row["close"])
        result.append((
            row["date"], c,
            float(row.get("change", "0")),
            float(row.get("pct", "0")),
            float(row.get("z_score", "0")),
            float(row.get("open", str(c))),
            float(row.get("high", str(c))),
            float(row.get("low", str(c))),
            float(row.get("volume", "0")),
            row.get("fetch_time", ""),
        ))
    return result


def save_history(records: list[Record]) -> None:
    with open(HISTORY_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "close", "change", "pct", "z_score", "open", "high", "low", "volume", "fetch_time"])
        for r in records:
            fetch_time: str = r[9] if len(r) > 9 else ""
            open_ = r[5] if len(r) > 5 else r[1]
            high_ = r[6] if len(r) > 6 else r[1]
            low_ = r[7] if len(r) > 7 else r[1]
            volume = r[8] if len(r) > 8 else 0
            w.writerow([r[0], f"{r[1]:.2f}", f"{r[2]:.2f}", f"{r[3]:.2f}", f"{r[4]:.2f}",
                       f"{open_:.2f}", f"{high_:.2f}", f"{low_:.2f}", f"{volume:.0f}", fetch_time])


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


def save_feedback(date: str, subject: str, rating: str = "") -> None:
    try:
        has_header: bool = os.path.exists(FEEDBACK_FILE)
        with open(FEEDBACK_FILE, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if not has_header:
                w.writerow(["date", "subject", "rating", "created_at"])
            w.writerow([date, subject, rating, datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")])
    except Exception:
        pass


def load_feedback() -> list[dict[str, str]]:
    if not os.path.exists(FEEDBACK_FILE):
        return []
    try:
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


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
        logger.info("历史数据已存在，跳过初始化")
        return
    data: dict[str, Any] = fetch_yahoo_chart("5y")
    if not data.get("chart", {}).get("result"):
        logger.warning("获取历史数据失败，跳过初始化")
        return
    results: dict[str, Any] = data["chart"]["result"][0]
    pcts: list[float] = []
    records: list[Record] = []
    prev: float | None = None
    timestamps: list[int] = results["timestamp"]
    quote: dict[str, Any] = results["indicators"]["quote"][0]
    closes: list[float | None] = quote["close"]
    opens: list[float | None] = quote.get("open", [])
    highs: list[float | None] = quote.get("high", [])
    lows: list[float | None] = quote.get("low", [])
    volumes: list[float | None] = quote.get("volume", [])
    for i, (ts, c) in enumerate(zip(timestamps, closes)):
        if c is not None:
            date: str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
            chg: float = c - prev if prev else 0
            pct: float = chg / prev * 100 if prev else 0
            o: float = opens[i] if i < len(opens) and opens[i] is not None else c
            h: float = highs[i] if i < len(highs) and highs[i] is not None else c
            l: float = lows[i] if i < len(lows) and lows[i] is not None else c
            v: float = float(volumes[i]) if i < len(volumes) and volumes[i] is not None else 0
            pcts.append(pct)
            records.append((date, c, chg, pct, calc_z_score(pcts), o, h, l, v, ""))
            prev = c
    save_history(records)
    logger.info("历史数据已初始化，共 %s 条", len(records))


def get_today_data(multiplier: float = 1.0) -> tuple[str, float, str, float, float, float, float, float, float, float]:
    data: dict[str, Any] = fetch_yahoo_chart("1d")
    if not data.get("chart", {}).get("result"):
        logger.warning("获取今日数据失败，使用本地缓存")
        records_cache: list[Record] = load_history()
        if records_cache:
            last: Record = records_cache[-1]
            open_ = last[5] if len(last) > 5 else last[1]
            high_ = last[6] if len(last) > 6 else last[1]
            low_ = last[7] if len(last) > 7 else last[1]
            volume = last[8] if len(last) > 8 else 0
            return (f"使用缓存数据：{last[0]} 收盘 {last[1]:.2f}", last[3], last[0], last[1], last[2], last[4], open_, high_, low_, volume)
        return ("无法获取数据", 0.0, "", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    results: dict[str, Any] = data["chart"]["result"][0]
    meta: dict[str, Any] = results["meta"]
    quote: dict[str, Any] = results["indicators"]["quote"][0]
    closes: list[float | None] = quote["close"]

    latest_close: float | None = meta.get("regularMarketPrice")
    if latest_close is None:
        valid: list[float] = [c for c in closes if c is not None]
        latest_close = valid[-1]
    latest_close = float(latest_close)

    prev_close: float = float(meta.get("chartPreviousClose", 0))
    if not prev_close:
        valid = [c for c in closes if c is not None]
        prev_close = valid[-2] if len(valid) >= 2 else latest_close

    opens: list[float | None] = quote.get("open", [])
    highs: list[float | None] = quote.get("high", [])
    lows: list[float | None] = quote.get("low", [])
    volumes: list[float | None] = quote.get("volume", [])
    valid_o: list[float] = [o for o in opens if o is not None]
    valid_h: list[float] = [h for h in highs if h is not None]
    valid_l: list[float] = [l for l in lows if l is not None]
    valid_v: list[float] = [v for v in volumes if v is not None]
    open_price: float = valid_o[-1] if valid_o else latest_close
    high_price: float = valid_h[-1] if valid_h else latest_close
    low_price: float = valid_l[-1] if valid_l else latest_close
    volume: float = valid_v[-1] if valid_v else 0

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
    return msg, pct, data_date, latest_close, change, z_score, open_price, high_price, low_price, volume
