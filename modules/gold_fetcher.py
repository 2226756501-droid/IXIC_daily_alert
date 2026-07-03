import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from modules.config import get_env
from modules.gold_storage import load_gold_history, save_gold_history
from modules.gold_types import GoldRecord
from modules.forex import fetch_usdcny_rate, cny as cny_convert
from modules.stats import calc_z_score, describe_z
from modules.yahoo_client import fetch_chart, safe_json

logger: logging.Logger = logging.getLogger(__name__)

GOLD_SYMBOL: str = get_env("GOLD_SYMBOL", "GC=F")


def fetch_gold_chart(range_str: str = "1d") -> dict[str, Any]:
    return fetch_chart(range_str, symbol=GOLD_SYMBOL)


def _parse_records(data: dict[str, Any], existing_dates: set[str]) -> tuple[list[GoldRecord], list[float]]:
    results: dict[str, Any] = data["chart"]["result"][0]
    timestamps: list[int] = results["timestamp"]
    quote: dict[str, Any] = results["indicators"]["quote"][0]
    closes: list[float | None] = quote["close"]
    opens: list[float | None] = quote.get("open", [])
    highs: list[float | None] = quote.get("high", [])
    lows: list[float | None] = quote.get("low", [])
    volumes: list[float | None] = quote.get("volume", [])
    gold_records: list[GoldRecord] = []
    pcts: list[float] = []
    prev: float | None = None
    for i, (ts, c) in enumerate(zip(timestamps, closes)):
        if c is not None:
            date: str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
            if date in existing_dates:
                prev = c
                continue
            chg: float = c - prev if prev else 0
            pct: float = chg / prev * 100 if prev else 0
            o: float = opens[i] if i < len(opens) and opens[i] is not None else c
            h: float = highs[i] if i < len(highs) and highs[i] is not None else c
            l: float = lows[i] if i < len(lows) and lows[i] is not None else c
            v: float = float(volumes[i]) if i < len(volumes) and volumes[i] is not None else 0
            gold_records.append(GoldRecord(date, c, chg, pct, o, h, l, v, ""))
            pcts.append(pct)
            prev = c
    return gold_records, pcts


def init_gold_history() -> None:
    records: list[GoldRecord] = load_gold_history()
    existing: set[str] = {r.date for r in records}
    data: dict[str, Any] = fetch_gold_chart("5y")
    if not data.get("chart", {}).get("result"):
        logger.warning("获取黄金历史数据失败")
        return
    new_records, _ = _parse_records(data, existing)
    if new_records:
        records.extend(new_records)
        records.sort(key=lambda r: r.date)
        save_gold_history(records)
        logger.info("黄金历史数据已更新，新增 %s 条，共 %s 条", len(new_records), len(records))
    else:
        logger.info("黄金历史数据共 %s 条，无需更新", len(records))


def get_today_gold() -> tuple[str, float, str, float, float, float, float, float, float, float, float, float]:
    data: dict[str, Any] = fetch_gold_chart("1d")
    if not data.get("chart", {}).get("result"):
        logger.warning("获取今日黄金数据失败，使用本地缓存")
        records_cache: list[GoldRecord] = load_gold_history()
        if records_cache:
            last: GoldRecord = records_cache[-1]
            rate = fetch_usdcny_rate()
            cny_price = cny_convert(last.close, rate)
            hist_pcts = [r.pct for r in records_cache]
            z = calc_z_score(hist_pcts + [last.pct])
            return (f"使用缓存数据：{last.date} 收盘 ${last.close:.2f}", last.pct, last.date, last.close, last.change, last.open, last.high, last.low, last.volume, cny_price, rate, z)
        return ("无法获取数据", 0.0, "", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 7.25, 0.0)

    results: dict[str, Any] = data["chart"]["result"][0]
    meta: dict[str, Any] = results["meta"]
    quote: dict[str, Any] = results["indicators"]["quote"][0]
    closes: list[float | None] = quote["close"]

    latest_close: float | None = meta.get("regularMarketPrice")
    if latest_close is None:
        valid: list[float] = [c for c in closes if c is not None]
        latest_close = valid[-1] if valid else 0.0
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

    records: list[GoldRecord] = load_gold_history()
    new_record: GoldRecord = GoldRecord(data_date, latest_close, change, pct, open_price, high_price, low_price, volume, datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))

    updated: bool = False
    for i, rec in enumerate(records):
        if rec.date == data_date:
            records[i] = new_record
            updated = True
            break
    if not updated:
        records.append(new_record)
    save_gold_history(records)

    rate: float = fetch_usdcny_rate()
    cny_price: float = cny_convert(latest_close, rate)

    hist_pcts: list[float] = [r.pct for r in records]
    z: float = calc_z_score(hist_pcts + [pct])
    level: str = describe_z(z)

    msg: str = (
        f"黄金期货收于 ${latest_close:.2f}/盎司（约 ¥{cny_price:.2f}），"
        f"较前一交易日{direction} ${abs(change):.2f}，涨跌幅 {pct:+.2f}%。\n"
        f"数据日期 {data_date}，汇率 {rate:.4f}，异常度 Z = {z:.2f}（{level}）"
    )
    return msg, pct, data_date, latest_close, change, open_price, high_price, low_price, volume, cny_price, rate, z
