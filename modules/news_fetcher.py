import logging
import xml.etree.ElementTree as ET
from typing import Any

import requests

logger: logging.Logger = logging.getLogger(__name__)

RSS_URLS: list[str] = [
    "https://finance.yahoo.com/news/rssindex",
    "https://news.google.com/rss/search?q=NASDAQ&hl=en-US&gl=US&ceid=US:en",
]

NASDAQ_KEYWORDS: list[str] = ["nasdaq", "ixic", "科技股", "纳斯达克", "美联储", "interest rate"]


def fetch_nasdaq_news(max_items: int = 5) -> list[str]:
    headlines: list[str] = []
    for url in RSS_URLS:
        try:
            resp: requests.Response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            root: Any = ET.fromstring(resp.content)
            for item in root.iter("item"):
                title: str | None = item.findtext("title")
                link: str | None = item.findtext("link")
                if title and any(kw in title.lower() for kw in NASDAQ_KEYWORDS):
                    headlines.append(f"{title}\n  {link}")
                if len(headlines) >= max_items:
                    break
        except Exception as e:
            logger.warning("RSS 抓取失败 %s: %s", url, e)
            continue
        if len(headlines) >= max_items:
            break
    return headlines[:max_items]
