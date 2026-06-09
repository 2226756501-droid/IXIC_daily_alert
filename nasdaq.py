import requests
import smtplib
import os
from email.mime.text import MIMEText
from datetime import datetime, timezone

def get_nasdaq():
    url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EIXIC?range=5d&interval=1d"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=10)
    data = resp.json()
    results = data["chart"]["result"][0]
    timestamps = results["timestamp"]
    closes = [c for c in results["indicators"]["quote"][0]["close"] if c is not None]
    opens = [o for o in results["indicators"]["quote"][0]["open"] if o is not None]
    latest_close = closes[-1]
    prev_close = closes[-2] if len(closes) >= 2 else opens[-1]
    change = latest_close - prev_close
    pct = change / prev_close * 100
    today = datetime.fromtimestamp(timestamps[-1], tz=timezone.utc).strftime("%Y-%m-%d")
    direction = "📈 涨" if change >= 0 else "📉 跌"
    msg = f"今日（{today}）纳斯达克综合指数收于 {latest_close:.2f} 点，较前一交易日{direction} {abs(change):.2f} 点，涨跌幅 {pct:+.2f}%。"
    return msg, pct, today

def send_email(subject, body):
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.qq.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "465"))
    email_user = os.environ.get("EMAIL_USER")
    email_pass = os.environ.get("EMAIL_PASS")
    notify_email = os.environ.get("NOTIFY_EMAIL", email_user)
    if not email_user or not email_pass:
        return
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = email_user
    msg["To"] = notify_email
    with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
        server.login(email_user, email_pass)
        server.send_message(msg)

if __name__ == "__main__":
    msg, pct, today = get_nasdaq()
    print(msg)
    send_email(f"【纳斯达克收盘】{today} 涨跌幅 {pct:+.2f}%", msg)
    print(">> 邮件已发送")
