import logging
from typing import Any

from modules.gold_storage import load_gold_history
from modules.gold_types import GoldRecord
from modules.webhook import send_webhook
from modules.config import get_env

logger: logging.Logger = logging.getLogger(__name__)

GOLD_ALERT_Z: float = 2.0


def check_gold_alert(z: float, close: float, pct: float, cny_price: float, data_date: str) -> bool:
    threshold: float = float(get_env("GOLD_ALERT_Z", str(GOLD_ALERT_Z)))
    if abs(z) < threshold:
        return False

    direction: str = "📈 大涨" if z > 0 else "📉 大跌"
    title: str = f"🥇 黄金{direction}预警"
    body: str = (
        f"黄金价格异常波动\n"
        f"日期：{data_date}\n"
        f"美元价格：${close:.2f}/盎司\n"
        f"人民币价格：¥{cny_price:.2f}\n"
        f"涨跌幅：{pct:+.2f}%\n"
        f"异常度 Z：{z:.2f}（超过 {threshold}σ 阈值）"
    )

    from modules.mailer import send_email
    send_email(title, body)
    send_webhook(title, body)

    records: list[GoldRecord] = load_gold_history()
    recent: list[GoldRecord] = records[-5:] if len(records) >= 5 else records
    details: str = "\n".join(
        f"  {r.date}: ${r.close:.2f} ({r.pct:+.2f}%)" for r in recent
    )
    logger.info("黄金预警触发\n%s\n近期数据:\n%s", body, details)
    return True
