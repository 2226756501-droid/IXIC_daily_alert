"""Backfill OHLC + volume for historical records missing these columns.
Usage: python backfill_ohlc.py
"""
import csv
import logging
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger: logging.Logger = logging.getLogger("backfill")

HISTORY_FILE: str = os.path.join(os.path.dirname(__file__), "history.csv")


def _fetch_month_range(year: int, month: int) -> dict:
    import requests
    from calendar import monthrange
    last_day: int = monthrange(year, month)[1]
    period1: int = int(datetime(year, month, 1, tzinfo=timezone.utc).timestamp())
    period2: int = int(datetime(year, month, last_day, 23, 59, tzinfo=timezone.utc).timestamp())
    url: str = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/%5EIXIC?"
        f"period1={period1}&period2={period2}&interval=1d"
    )
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning("获取 %d-%d 数据失败: %s", year, month, e)
        return {}


def main() -> None:
    if not os.path.exists(HISTORY_FILE):
        logger.error("history.csv 不存在")
        return

    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        rows: list[dict[str, str]] = list(csv.DictReader(f))

    # Check which records need backfill
    need_fill: list[int] = []
    for i, row in enumerate(rows):
        vol: str = row.get("volume", "")
        if not vol or float(vol) == 0:
            need_fill.append(i)

    if not need_fill:
        logger.info("所有记录已有 OHLC/Volume 数据，无需回填")
        return

    logger.info("发现 %d 条记录缺少数据，开始回填", len(need_fill))

    # Group by month for efficient fetching
    months: set[tuple[int, int]] = set()
    for i in need_fill:
        date_str: str = rows[i]["date"]
        dt: datetime = datetime.strptime(date_str, "%Y-%m-%d")
        months.add((dt.year, dt.month))

    date_map: dict[str, dict[str, float]] = {}
    for year, month in sorted(months):
        data = _fetch_month_range(year, month)
        results = data.get("chart", {}).get("result", [])
        if not results:
            continue
        r = results[0]
        timestamps: list[int] = r.get("timestamp", [])
        quote = r.get("indicators", {}).get("quote", [{}])[0]
        opens: list = quote.get("open", [])
        highs: list = quote.get("high", [])
        lows: list = quote.get("low", [])
        closes: list = quote.get("close", [])
        volumes: list = quote.get("volume", [])

        for j, ts in enumerate(timestamps):
            d: str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
            c = closes[j] if j < len(closes) and closes[j] is not None else 0
            date_map[d] = {
                "open": float(opens[j]) if j < len(opens) and opens[j] is not None else float(c),
                "high": float(highs[j]) if j < len(highs) and highs[j] is not None else float(c),
                "low": float(lows[j]) if j < len(lows) and lows[j] is not None else float(c),
                "volume": float(volumes[j]) if j < len(volumes) and volumes[j] is not None else 0,
            }
        logger.info("已加载 %d-%d (%d 条)", year, month, len(date_map))

    # Backfill
    filled: int = 0
    for i in need_fill:
        d: str = rows[i]["date"]
        c: float = float(rows[i]["close"])
        info = date_map.get(d)
        if info:
            rows[i]["open"] = f"{info['open']:.2f}"
            rows[i]["high"] = f"{info['high']:.2f}"
            rows[i]["low"] = f"{info['low']:.2f}"
            rows[i]["volume"] = f"{info['volume']:.0f}"
            filled += 1
        else:
            rows[i]["open"] = rows[i].get("open", f"{c:.2f}")
            rows[i]["high"] = rows[i].get("high", f"{c:.2f}")
            rows[i]["low"] = rows[i].get("low", f"{c:.2f}")
            rows[i]["volume"] = rows[i].get("volume", "0")

    fieldnames: list[str] = ["date", "close", "change", "pct", "z_score", "open", "high", "low", "volume", "fetch_time"]
    with open(HISTORY_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    logger.info("回填完成：%d / %d 条已填充", filled, len(need_fill))


if __name__ == "__main__":
    main()
