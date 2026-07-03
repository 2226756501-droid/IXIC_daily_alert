import logging
import time
from typing import Any

import requests

from modules.config import get_env

logger: logging.Logger = logging.getLogger(__name__)


def request_with_retry(url: str, headers: dict[str, str], max_retries: int = 3) -> requests.Response | None:
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
    resp: requests.Response | None = request_with_retry(url, {"User-Agent": "Mozilla/5.0"})
    if resp is None:
        return {}
    try:
        return resp.json()
    except Exception:
        return {}


def fetch_chart(range_str: str = "1d", symbol: str | None = None) -> dict[str, Any]:
    ticker: str = symbol or get_env("NASDAQ_SYMBOL", "^IXIC")
    encoded: str = ticker.replace("^", "%5E")
    url: str = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?range={range_str}&interval=1d"
    resp: requests.Response | None = request_with_retry(url, {"User-Agent": "Mozilla/5.0"})
    if resp is None:
        return _fallback_fetch(ticker, range_str)
    try:
        return resp.json()
    except Exception as e:
        logger.warning("Yahoo Finance API 解析失败: %s", e)
        return _fallback_fetch(ticker, range_str)


def _fallback_fetch(symbol: str, range_str: str) -> dict[str, Any]:
    logger.info("尝试备用数据源: query2.finance.yahoo.com")
    encoded: str = symbol.replace("^", "%5E")
    url: str = f"https://query2.finance.yahoo.com/v8/finance/chart/{encoded}?range={range_str}&interval=1d"
    resp = request_with_retry(url, {"User-Agent": "Mozilla/5.0"})
    if resp is None:
        logger.warning("备用数据源也失败")
        return {}
    try:
        return resp.json()
    except Exception as e:
        logger.warning("备用数据源解析失败: %s", e)
        return {}
