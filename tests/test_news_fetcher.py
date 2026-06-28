from unittest.mock import patch, MagicMock

from modules.news_fetcher import fetch_nasdaq_news, RSS_URLS, NASDAQ_KEYWORDS


def test_fetch_nasdaq_news_empty_on_error() -> None:
    with patch("modules.news_fetcher.requests.get") as mock_get:
        mock_get.side_effect = Exception("Network error")
        result = fetch_nasdaq_news()
        assert result == []


def test_fetch_nasdaq_news_respects_max_items() -> None:
    fake_xml = b"""<?xml version="1.0"?>
    <rss><channel>
        <item><title>NASDAQ rises today</title><link>http://example.com/1</link></item>
        <item><title>Tech stocks gain</title><link>http://example.com/2</link></item>
        <item><title>Market update</title><link>http://example.com/3</link></item>
        <item><title>NASDAQ hits record</title><link>http://example.com/4</link></item>
    </channel></rss>"""
    with patch("modules.news_fetcher.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.content = fake_xml
        mock_get.return_value = mock_response
        result = fetch_nasdaq_news(max_items=2)
        assert len(result) == 2


def test_fetch_nasdaq_news_filters_by_keywords() -> None:
    fake_xml = b"""<?xml version="1.0"?>
    <rss><channel>
        <item><title>Sports scores today</title><link>http://example.com/1</link></item>
        <item><title>NASDAQ rallies on tech gains</title><link>http://example.com/2</link></item>
    </channel></rss>"""
    mock_response = MagicMock()
    mock_response.content = fake_xml
    with patch("modules.news_fetcher.requests.get") as mock_get:
        mock_get.side_effect = [mock_response, Exception("Second URL fails")]
        result = fetch_nasdaq_news(max_items=5)
        assert len(result) == 1
        assert "NASDAQ" in result[0]
        assert "Sports" not in result[0]


def test_rss_urls_configured() -> None:
    assert len(RSS_URLS) >= 2


def test_nasdaq_keywords_configured() -> None:
    assert len(NASDAQ_KEYWORDS) >= 3
    assert all(isinstance(k, str) for k in NASDAQ_KEYWORDS)
