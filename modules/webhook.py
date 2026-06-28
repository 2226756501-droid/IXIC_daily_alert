import json
import logging
from typing import Any

import requests

from modules.config import get_env

logger: logging.Logger = logging.getLogger(__name__)

WECOM_KEY: str = get_env("WECOM_WEBHOOK_KEY", "")
DINGTALK_TOKEN: str = get_env("DINGTALK_WEBHOOK_TOKEN", "")
SLACK_URL: str = get_env("SLACK_WEBHOOK_URL", "")
PUSHOVER_USER: str = get_env("PUSHOVER_USER_KEY", "")
PUSHOVER_TOKEN: str = get_env("PUSHOVER_APP_TOKEN", "")


def send_wecom(title: str, message: str) -> bool:
    if not WECOM_KEY:
        return False
    url: str = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={WECOM_KEY}"
    payload: dict[str, Any] = {
        "msgtype": "markdown",
        "markdown": {"content": f"## {title}\n{message}"},
    }
    try:
        resp: requests.Response = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("企业微信推送成功")
        return True
    except Exception as e:
        logger.warning("企业微信推送失败: %s", e)
        return False


def send_dingtalk(title: str, message: str) -> bool:
    if not DINGTALK_TOKEN:
        return False
    url: str = f"https://oapi.dingtalk.com/robot/send?access_token={DINGTALK_TOKEN}"
    payload: dict[str, Any] = {
        "msgtype": "text",
        "text": {"content": f"{title}\n{message}"},
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("钉钉推送成功")
        return True
    except Exception as e:
        logger.warning("钉钉推送失败: %s", e)
        return False


def send_slack(title: str, message: str) -> bool:
    if not SLACK_URL:
        return False
    payload: dict[str, Any] = {
        "blocks": [
            {"type": "header", "text": {"type": "plain_text", "text": title}},
            {"type": "section", "text": {"type": "mrkdwn", "text": message}},
        ],
    }
    try:
        resp = requests.post(SLACK_URL, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("Slack 推送成功")
        return True
    except Exception as e:
        logger.warning("Slack 推送失败: %s", e)
        return False


def send_pushover(title: str, message: str) -> bool:
    if not PUSHOVER_USER or not PUSHOVER_TOKEN:
        return False
    payload: dict[str, str] = {
        "token": PUSHOVER_TOKEN,
        "user": PUSHOVER_USER,
        "title": title,
        "message": message,
    }
    try:
        resp = requests.post("https://api.pushover.net/1/messages.json", data=payload, timeout=10)
        resp.raise_for_status()
        logger.info("Pushover 推送成功")
        return True
    except Exception as e:
        logger.warning("Pushover 推送失败: %s", e)
        return False


SENDERS: list[dict[str, Any]] = [
    {"name": "企业微信", "func": send_wecom},
    {"name": "钉钉", "func": send_dingtalk},
    {"name": "Slack", "func": send_slack},
    {"name": "Pushover", "func": send_pushover},
]


def send_webhook(subject: str, body: str) -> int:
    sent: int = 0
    for sender in SENDERS:
        if sender["func"](subject, body):
            sent += 1
    if sent:
        logger.info("Webhook 推送完成：%d 个渠道", sent)
    return sent
