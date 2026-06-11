import requests
import xml.etree.ElementTree as ET

RSS_URLS = [
    "https://finance.yahoo.com/news/rssindex",
    "https://news.google.com/rss/search?q=NASDAQ&hl=en-US&gl=US&ceid=US:en",
]


def fetch_nasdaq_news(max_items=3):
    headlines = []
    for url in RSS_URLS:
        try:
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            root = ET.fromstring(resp.content)
            for item in root.iter("item"):
                title = item.findtext("title")
                link = item.findtext("link")
                if title and "nasdaq" in title.lower():
                    headlines.append(f"{title}\n  {link}")
                if len(headlines) >= max_items:
                    break
        except Exception:
            continue
        if len(headlines) >= max_items:
            break
    return headlines[:max_items]


if __name__ == "__main__":
    for h in fetch_nasdaq_news():
        print(h)
