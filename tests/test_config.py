from unittest.mock import patch

from modules.config import get_env, get_email_config


def test_get_env_default() -> None:
    assert get_env("NONEXISTENT_KEY") == ""


def test_get_env_with_default() -> None:
    assert get_env("NONEXISTENT_KEY", "fallback") == "fallback"


@patch.dict("os.environ", {}, clear=True)
def test_email_config_defaults() -> None:
    cfg = get_email_config()
    assert cfg["server"] == "smtp.qq.com"
    assert cfg["port"] == 465
    assert cfg["user"] == ""
    assert cfg["password"] == ""
