import logging
import time
from typing import Any

from modules.config import get_env
from modules.yahoo_client import request_with_retry

logger: logging.Logger = logging.getLogger(__name__)

CNY_SYMBOL: str = get_env("CNY_SYMBOL", "CNY=X")

_cache: dict[str, Any] = {"rate": 0.0, "time": 0.0}
_cache_ttl: int = 300


def fetch_usdcny_rate(force: bool = False) -> float:
    now: float = time.time()
    if not force and _cache["rate"] and (now - _cache["time"]) < _cache_ttl:
        return _cache["rate"]
    url: str = f"https://query1.finance.yahoo.com/v8/finance/chart/{CNY_SYMBOL}?range=1d&interval=1d"
    resp = request_with_retry(url, {"User-Agent": "Mozilla/5.0"})
    if resp is None:
        if _cache["rate"]:
            return _cache["rate"]
        logger.warning("获取美元/人民币汇率失败")
        return 7.25
    try:
        data: dict[str, Any] = resp.json()
        result = data.get("chart", {}).get("result", [])
        if not result:
            return _cache["rate"] if _cache["rate"] else 7.25
        meta = result[0].get("meta", {})
        rate = meta.get("regularMarketPrice")
        if rate is None:
            quote = result[0].get("indicators", {}).get("quote", [{}])[0]
            closes = [c for c in quote.get("close", []) if c is not None]
            rate = closes[-1] if closes else 7.25
        rate = float(rate)
        _cache["rate"] = rate
        _cache["time"] = now
        return rate
    except Exception as e:
        if _cache["rate"]:
            return _cache["rate"]
        logger.warning("美元/人民币汇率解析失败: %s", e)
        return 7.25


def cny(usd_price: float, rate: float | None = None) -> float:
    if rate is None:
        rate = fetch_usdcny_rate()
    return usd_price * rate
