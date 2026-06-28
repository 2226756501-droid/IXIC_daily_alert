import logging
import smtplib
from email.mime.text import MIMEText
from typing import Any

from modules.config import get_email_config
from modules.agent_engine import generate_email
from modules.types import EmailContext

logger: logging.Logger = logging.getLogger(__name__)


def build_email(ctx: EmailContext) -> tuple[str, str]:
    result = generate_email(ctx)
    if result:
        logger.info("AI 生成邮件成功")
        return result
    logger.info("AI 邮件生成不可用，使用模板")
    return _template_email(ctx)


def _template_email(ctx: EmailContext) -> tuple[str, str]:
    body: str = ctx["msg"]
    subject: str = f"【纳斯达克数据】{ctx['date']} 涨跌幅 {ctx['pct']:+.2f}%"

    if ctx.get("news"):
        body += "\n────\n📰 今日相关新闻：\n" + "\n".join(f"{i+1}. {h}" for i, h in enumerate(ctx["news"]))
    if ctx.get("drawdown"):
        dd: dict[str, Any] = ctx["drawdown"]
        body += f"\n────\n📉 近3月最大回撤：{dd['max_drawdown_pct']}%（{dd['date']}）"
        subject = f"【异常时段】纳斯达克连跌{ctx['drops']}天，近3月最大回撤 {dd['max_drawdown_pct']}%"
    if ctx.get("recovery"):
        body += f"\n────\n✅ 异常时段结束（连跌{ctx['drops']}天后恢复）"
        subject = f"【纳斯达克数据】异常时段结束 - {ctx['date']} 涨跌幅 {ctx['pct']:+.2f}%"
    if ctx.get("advice"):
        body += "\n" + ctx["advice"]

    return subject, body


def send_email(subject: str, body: str) -> None:
    cfg: dict[str, Any] = get_email_config()
    if not cfg["user"] or not cfg["password"]:
        logger.warning("邮箱未配置，跳过发送")
        return
    msg: Any = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = cfg["user"]
    msg["To"] = cfg["notify"]
    with smtplib.SMTP_SSL(cfg["server"], cfg["port"]) as server:
        server.login(cfg["user"], cfg["password"])
        server.send_message(msg)
