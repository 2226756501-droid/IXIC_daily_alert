import io, sys
import requests
import smtplib
import os
import csv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from email.mime.text import MIMEText
from datetime import datetime, timezone

HISTORY_FILE = "history.csv"


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return [(row["date"], float(row["close"]), float(row.get("pct", "0")))
                for row in csv.DictReader(f)]


def save_history(records):
    with open(HISTORY_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "close", "pct"])
        for date, close, pct in records:
            w.writerow([date, f"{close:.2f}", f"{pct:.2f}"])


def fetch_chart(range_str):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/%5EIXIC?range={range_str}&interval=1d"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=10)
    return resp.json()


def init_history():
    if load_history():
        return
    data = fetch_chart("1y")
    results = data["chart"]["result"][0]
    records = []
    prev = None
    for ts, c in zip(results["timestamp"], results["indicators"]["quote"][0]["close"]):
        if c is not None:
            date = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
            pct = (c - prev) / prev * 100 if prev else 0
            records.append((date, c, pct))
            prev = c
    save_history(records)
    print(f">> 历史数据已初始化，共 {len(records)} 条")


def get_today_data():
    data = fetch_chart("5d")
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
    return msg, pct, today, latest_close

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
    init_history()
    msg, pct, today, close = get_today_data()
    print(msg)

    records = load_history()
    if not records or records[-1][0] != today:
        prev_close = records[-1][1] if records else close
        pct_record = (close - prev_close) / prev_close * 100
        records.append((today, close, pct_record))
        save_history(records)
        print(f">> 已记录 {today} 数据")

    send_email(f"【纳斯达克收盘】{today} 涨跌幅 {pct:+.2f}%", msg)
    print(">> 邮件已发送")
