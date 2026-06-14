import os
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR: Path = Path(__file__).resolve().parent.parent


def get_env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def get_email_config() -> dict[str, Any]:
    return {
        "server": get_env("SMTP_SERVER", "smtp.qq.com"),
        "port": int(get_env("SMTP_PORT", "465")),
        "user": get_env("EMAIL_USER", ""),
        "password": get_env("EMAIL_PASS", ""),
        "notify": get_env("NOTIFY_EMAIL", get_env("EMAIL_USER", "")),
    }



