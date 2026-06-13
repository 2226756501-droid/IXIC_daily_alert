import xml.etree.ElementTree as ET
from typing import Any

import requests

RSS_URLS: list[str] = [
    "https://finance.yahoo.com/news/rssindex",
    "https://news.google.com/rss/search?q=NASDAQ&hl=en-US&gl=US&ceid=US:en",
]


def fetch_nasdaq_news(max_items: int = 3) -> list[str]:
    headlines: list[str] = []
    for url in RSS_URLS:
        try:
            resp: requests.Response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            root: Any = ET.fromstring(resp.content)
            for item in root.iter("item"):
                title: str | None = item.findtext("title")
                link: str | None = item.findtext("link")
                if title and "nasdaq" in title.lower():
                    headlines.append(f"{title}\n  {link}")
                if len(headlines) >= max_items:
                    break
        except Exception:
            continue
        if len(headlines) >= max_items:
            break
    return headlines[:max_items]
