import email
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Any

from modules.storage import load_feedback, save_feedback
from modules.config import get_env

logger: logging.Logger = logging.getLogger(__name__)

IMAP_SERVER: str = "imap.qq.com"
IMAP_PORT: int = 993
SEARCH_KEYWORDS: list[str] = ["纳斯达克", "NASDAQ", "nasdaq"]
LOOKBACK_HOURS: int = 48


def _decode_str(s: str | None) -> str:
    if s is None:
        return ""
    try:
        parts = email.header.decode_header(s)
        result: list[str] = []
        for byte_or_str, charset in parts:
            if isinstance(byte_or_str, bytes):
                result.append(byte_or_str.decode(charset or "utf-8", errors="replace"))
            else:
                result.append(str(byte_or_str))
        return " ".join(result)
    except Exception:
        return str(s)


def _parse_body(msg: Any) -> str:
    body: str = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype: str = part.get_content_type()
            if ctype == "text/plain":
                try:
                    payload: bytes = part.get_payload(decode=True)
                    if payload:
                        charset: str = part.get_content_charset() or "utf-8"
                        body += payload.decode(charset, errors="replace")
                except Exception:
                    continue
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or "utf-8"
                body = payload.decode(charset, errors="replace")
        except Exception:
            pass
    return body


def _extract_rating(body: str) -> str:
    body_clean: str = body.strip()
    lines: list[str] = body_clean.splitlines()
    for line in lines:
        line = line.strip()
        if re.match(r"^1\s*$", line):
            return "1"
        if re.match(r"^2\s*$", line):
            return "2"
        if re.match(r"^满意\s*$", line):
            return "1"
        if re.match(r"^不满意\s*$", line):
            return "2"
    return ""


def check_feedback() -> int:
    user: str = get_env("EMAIL_USER", "")
    password: str = get_env("EMAIL_PASS", "")
    if not user or not password:
        logger.warning("邮箱未配置，跳过反馈检查")
        return 0

    import imaplib

    updated: int = 0
    existing: list[dict[str, str]] = load_feedback()

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(user, password)
        mail.select("INBOX")

        since_date: str = (datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)).strftime("%d-%b-%Y")
        status, messages = mail.search(None, f'(SINCE "{since_date}")')
        if status != "OK":
            logger.warning("搜索邮件失败")
            mail.logout()
            return 0

        ids: list[str] = messages[0].split() if messages[0] else []
        logger.info("最近 %s 小时内有 %d 封邮件", LOOKBACK_HOURS, len(ids))

        for mid in ids:
            status, data = mail.fetch(mid, "(RFC822)")
            if status != "OK":
                continue

            raw_email: bytes = data[0][1]
            msg: Any = email.message_from_bytes(raw_email)
            subject: str = _decode_str(msg.get("Subject", "")).lower()

            is_reply: bool = subject.startswith("re:") or subject.startswith("回复")
            is_nasdaq: bool = any(kw.lower() in subject for kw in SEARCH_KEYWORDS)
            if not is_reply or not is_nasdaq:
                continue

            body: str = _parse_body(msg)
            rating: str = _extract_rating(body)
            if not rating:
                continue

            reply_subject: str = _decode_str(msg.get("Subject", ""))
            logger.info("检测到回复: %s -> 评分 %s", reply_subject, rating)

            matched: bool = False
            for fb in existing:
                if fb.get("rating") in ("", None):
                    fb["rating"] = rating
                    matched = True
                    updated += 1
                    break
            if not matched:
                save_feedback(
                    datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    reply_subject,
                    rating,
                )
                updated += 1

        mail.logout()
    except Exception as e:
        logger.error("IMAP 反馈检查失败: %s", e)
        return 0

    if updated:
        logger.info("已更新 %d 条反馈评分", updated)
    else:
        logger.info("未发现新的反馈回复")
    return updated
