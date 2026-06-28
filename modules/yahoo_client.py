import logging
import time
from typing import Any

import requests

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


def fetch_chart(range_str: str = "1d") -> dict[str, Any]:
    url: str = f"https://query1.finance.yahoo.com/v8/finance/chart/%5EIXIC?range={range_str}&interval=1d"
    resp: requests.Response | None = request_with_retry(url, {"User-Agent": "Mozilla/5.0"})
    if resp is None:
        return {}
    try:
        return resp.json()
    except Exception as e:
        logger.warning("Yahoo Finance API 解析失败: %s", e)
        return {}
