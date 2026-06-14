from unittest.mock import patch, MagicMock
from typing import Any

from modules.agent_engine import generate_email, is_available


def test_generate_email_no_api_key() -> None:
    with patch("modules.agent_engine.get_deepseek_api_key", return_value=""):
        result = generate_email({"msg": "test"})
        assert result is None


def test_generate_email_api_error() -> None:
    ctx: dict[str, Any] = {
        "msg": "纳斯达克指数收于 25888.84 点，较前一交易日涨 79.18 点，涨跌幅 +0.31%。",
        "date": "2026-06-14", "pct": 0.31, "close": 25888.84, "change": 79.18,
        "z_score": 0.05, "is_down": False, "state": "normal",
        "drops": 0, "news": None, "drawdown": None,
        "recovery": False, "advice": None,
    }
    with patch("modules.agent_engine.is_available", return_value=True):
        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            mock_client.chat.completions.create.side_effect = Exception("API error")
            result = generate_email(ctx)
            assert result is None


def test_generate_email_success() -> None:
    ctx: dict[str, Any] = {
        "msg": "纳斯达克指数收于 25888.84 点，较前一交易日涨 79.18 点，涨跌幅 +0.31%。",
        "date": "2026-06-14", "pct": 0.31, "close": 25888.84, "change": 79.18,
        "z_score": 0.05, "is_down": False, "state": "normal",
        "drops": 0, "news": None, "drawdown": None,
        "recovery": False, "advice": None,
    }
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="纳斯达克日报 6月14日 小幅收涨 +0.31%\n\n今日纳斯达克收报 25,888.84 点，较前日上涨 79.18 点，涨幅 +0.31%。市场整体平稳。"))
    ]

    with patch("modules.agent_engine.is_available", return_value=True):
        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            mock_client.chat.completions.create.return_value = mock_response
            result = generate_email(ctx)

    assert result is not None
    subject, body = result
    assert "纳斯达克日报" in subject
    assert len(body) > 0
    assert len(subject) <= 60


def test_generate_email_subject_truncated() -> None:
    long_subject: str = "这是一个" * 20 + "标题"
    ctx: dict[str, Any] = {
        "msg": "test", "date": "2026-06-14", "pct": 0.0, "close": 25000.0,
        "change": 0.0, "z_score": 0.0, "is_down": False, "state": "normal",
        "drops": 0, "news": None, "drawdown": None,
        "recovery": False, "advice": None,
    }
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content=f"{long_subject}\n\nbody content"))
    ]

    with patch("modules.agent_engine.is_available", return_value=True):
        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            mock_client.chat.completions.create.return_value = mock_response
            result = generate_email(ctx)

    assert result is not None
    subject, _ = result
    assert len(subject) <= 60


def test_generate_email_with_news_and_drawdown() -> None:
    ctx: dict[str, Any] = {
        "msg": "纳斯达克指数收于 25000.00 点，较前一交易日跌 500.00 点，涨跌幅 -1.96%。",
        "date": "2026-06-14", "pct": -1.96, "close": 25000.0, "change": -500.0,
        "z_score": -2.5, "is_down": True, "state": "abnormal",
        "drops": 4, "news": ["科技股领跌", "美联储加息预期升温"],
        "drawdown": {"max_drawdown_pct": -8.5, "date": "2026-06-14"},
        "recovery": False, "advice": "历史参考：上次类似持续了3天",
    }
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(
            content="纳斯达克连跌4天，Z值-2.5进入异常\n\n今日纳指收报 25,000 点，跌幅 -1.96%。异常提醒：连跌4天，近3月最大回撤 -8.5%。综合判断：短期风险加大，建议关注美联储动向。"
        ))
    ]

    with patch("modules.agent_engine.is_available", return_value=True):
        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            mock_client.chat.completions.create.return_value = mock_response
            result = generate_email(ctx)

    assert result is not None
    subject, body = result
    assert len(subject) <= 60
    assert len(body) > 0
