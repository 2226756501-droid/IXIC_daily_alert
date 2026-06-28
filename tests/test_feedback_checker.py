from unittest.mock import patch, MagicMock

from modules.feedback_checker import _decode_str, _extract_rating, _get_reply_body


def test_decode_str_none() -> None:
    assert _decode_str(None) == ""


def test_decode_str_plain() -> None:
    assert _decode_str("hello") == "hello"


def test_extract_rating_1() -> None:
    assert _extract_rating("1") == "1"


def test_extract_rating_2() -> None:
    assert _extract_rating("2") == "2"


def test_extract_rating_satisfied() -> None:
    assert _extract_rating("满意") == "1"


def test_extract_rating_dissatisfied() -> None:
    assert _extract_rating("不满意") == "2"


def test_extract_rating_with_whitespace() -> None:
    assert _extract_rating("  1  ") == "1"


def test_extract_rating_empty() -> None:
    assert _extract_rating("") == ""


def test_extract_rating_no_match() -> None:
    assert _extract_rating("也许还行") == ""


def test_extract_rating_only_first_line() -> None:
    assert _extract_rating("1\n一些其他内容") == "1"


def test_get_reply_body_strips_quote() -> None:
    msg = MagicMock()
    msg.is_multipart.return_value = False
    msg.get_payload.return_value = b"1\n-----Original-----"
    msg.get_content_charset.return_value = "utf-8"
    result = _get_reply_body(msg)
    assert result == "1"
