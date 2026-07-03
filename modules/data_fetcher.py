import logging
from datetime import datetime, timezone
from typing import Any

from modules.stats import calc_z_score, describe_z
from modules.storage import (
    load_history, save_history, load_config,
    load_market_state, save_market_state,
    load_memory, save_memory, save_feedback, load_feedback,
)
from modules.types import Record, MarketState
from modules.yahoo_client import fetch_chart, safe_json

__all__ = [
    "init_history", "get_today_data", "Record",
    "load_history", "save_history", "load_config",
    "load_market_state", "save_market_state",
    "load_memory", "save_memory", "save_feedback", "load_feedback",
    "safe_json",
]

logger: logging.Logger = logging.getLogger(__name__)


def init_history() -> None:
    records: list[Record] = load_history()
    existing: set[str] = {r.date for r in records}
    data: dict[str, Any] = fetch_chart("5y")
    if not data.get("chart", {}).get("result"):
        if records:
            logger.info("历史数据共 %s 条，无法获取更新", len(records))
            return
        logger.warning("获取历史数据失败，跳过初始化")
        return
    results: dict[str, Any] = data["chart"]["result"][0]
    pcts: list[float] = [r.pct for r in records]
    timestamps: list[int] = results["timestamp"]
    quote: dict[str, Any] = results["indicators"]["quote"][0]
    closes: list[float | None] = quote["close"]
    opens: list[float | None] = quote.get("open", [])
    highs: list[float | None] = quote.get("high", [])
    lows: list[float | None] = quote.get("low", [])
    volumes: list[float | None] = quote.get("volume", [])
    new_records: list[Record] = []
    prev: float | None = records[-1].close if records else None
    for i, (ts, c) in enumerate(zip(timestamps, closes)):
        if c is not None:
            date: str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
            if date in existing:
                prev = c
                continue
            chg: float = c - prev if prev else 0
            pct: float = chg / prev * 100 if prev else 0
            o: float = opens[i] if i < len(opens) and opens[i] is not None else c
            h: float = highs[i] if i < len(highs) and highs[i] is not None else c
            l: float = lows[i] if i < len(lows) and lows[i] is not None else c
            v: float = float(volumes[i]) if i < len(volumes) and volumes[i] is not None else 0
            pcts.append(pct)
            new_records.append(Record(date, c, chg, pct, calc_z_score(pcts), o, h, l, v, ""))
            prev = c
    if new_records:
        records.extend(new_records)
        records.sort(key=lambda r: r.date)
        save_history(records)
        logger.info("历史数据已更新，新增 %s 条，共 %s 条", len(new_records), len(records))
    else:
        logger.info("历史数据共 %s 条，无需更新", len(records))


def get_today_data(multiplier: float = 1.0) -> tuple[str, float, str, float, float, float, float, float, float, float]:
    data: dict[str, Any] = fetch_chart("1d")
    if not data.get("chart", {}).get("result"):
        logger.warning("获取今日数据失败，使用本地缓存")
        records_cache: list[Record] = load_history()
        if records_cache:
            last: Record = records_cache[-1]
            return (f"使用缓存数据：{last.date} 收盘 {last.close:.2f}", last.pct, last.date, last.close, last.change, last.z_score, last.open, last.high, last.low, last.volume)
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
    hist_pcts: list[float] = [r.pct for r in records]
    z_score: float = calc_z_score(hist_pcts + [pct])
    level: str = describe_z(z_score, multiplier)

    msg: str = (
        f"纳斯达克指数收于 {latest_close:.2f} 点，"
        f"较前一交易日{direction} {abs(change):.2f} 点，涨跌幅 {pct:+.2f}%。\n"
        f"数据日期 {data_date}，异常度 Z = {z_score:.2f}（{level}）"
    )
    return msg, pct, data_date, latest_close, change, z_score, open_price, high_price, low_price, volume
