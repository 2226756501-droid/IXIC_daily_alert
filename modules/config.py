import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent


def get_env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def get_email_config() -> dict:
    return {
        "server": get_env("SMTP_SERVER", "smtp.qq.com"),
        "port": int(get_env("SMTP_PORT", "465")),
        "user": get_env("EMAIL_USER", ""),
        "password": get_env("EMAIL_PASS", ""),
        "notify": get_env("NOTIFY_EMAIL", get_env("EMAIL_USER", "")),
    }


def get_sensitivity() -> float:
    try:
        return float(get_env("SENSITIVITY_MULTIPLIER", "1.0"))
    except ValueError:
        return 1.0
