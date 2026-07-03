import logging
from typing import Any

from modules.yahoo_client import request_with_retry

logger: logging.Logger = logging.getLogger(__name__)

CNY_SYMBOL: str = "CNY=X"


def fetch_usdcny_rate() -> float:
    url: str = f"https://query1.finance.yahoo.com/v8/finance/chart/{CNY_SYMBOL}?range=1d&interval=1d"
    resp = request_with_retry(url, {"User-Agent": "Mozilla/5.0"})
    if resp is None:
        logger.warning("获取美元/人民币汇率失败")
        return 7.25
    try:
        data: dict[str, Any] = resp.json()
        result = data.get("chart", {}).get("result", [])
        if not result:
            return 7.25
        meta = result[0].get("meta", {})
        rate = meta.get("regularMarketPrice")
        if rate is None:
            quote = result[0].get("indicators", {}).get("quote", [{}])[0]
            closes = [c for c in quote.get("close", []) if c is not None]
            rate = closes[-1] if closes else 7.25
        return float(rate)
    except Exception as e:
        logger.warning("美元/人民币汇率解析失败: %s", e)
        return 7.25


def cny(usd_price: float, rate: float | None = None) -> float:
    if rate is None:
        rate = fetch_usdcny_rate()
    return usd_price * rate
