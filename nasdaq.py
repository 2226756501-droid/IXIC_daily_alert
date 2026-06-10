import io, sys
import requests
import smtplib
import os
import csv
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from email.mime.text import MIMEText
from datetime import datetime, timezone

HISTORY_FILE = "history.csv"
CONFIG_FILE = "threshold_config.json"


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"sensitivity_multiplier": 1.0}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return [(row["date"], float(row["close"]), float(row.get("change", "0")),
                 float(row.get("pct", "0")), float(row.get("z_score", "0")))
                for row in csv.DictReader(f)]


def save_history(records):
    with open(HISTORY_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "close", "change", "pct", "z_score", "fetch_time"])
        for r in records:
            fetch_time = r[5] if len(r) > 5 else ""
            w.writerow([r[0], f"{r[1]:.2f}", f"{r[2]:.2f}", f"{r[3]:.2f}", f"{r[4]:.2f}", fetch_time])


LOOKBACK = 20


def calc_z_score(pcts):
    window = pcts[:-1]
    if len(window) < 2:
        return 0.0
    mu = sum(window) / len(window)
    var = sum((x - mu) ** 2 for x in window) / (len(window) - 1)
    std = var ** 0.5
    return 0.0 if std == 0 else (pcts[-1] - mu) / std


def describe_z(z, multiplier=1.0):
    t1, t2, t3 = 1 * multiplier, 2 * multiplier, 3 * multiplier
    if abs(z) < t1:
        return "正常波动"
    if abs(z) < t2:
        return "值得注意"
    if abs(z) < t3:
        return "显著异常"
    return "极端行情"


def fetch_chart(range_str):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/%5EIXIC?range={range_str}&interval=1d"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=10)
    return resp.json()


def init_history():
    if load_history():
        return
    data = fetch_chart("5y")
    results = data["chart"]["result"][0]
    pcts, records = [], []
    prev = None
    for ts, c in zip(results["timestamp"], results["indicators"]["quote"][0]["close"]):
        if c is not None:
            date = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
            chg = c - prev if prev else 0
            pct = chg / prev * 100 if prev else 0
            pcts.append(pct)
            records.append((date, c, chg, pct, calc_z_score(pcts), ""))
            prev = c
    save_history(records)
    print(f">> 历史数据已初始化，共 {len(records)} 条")


def get_today_data(multiplier=1.0):
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

    records = load_history()
    hist_pcts = [r[3] for r in records]
    window = hist_pcts[-(LOOKBACK - 1):] + [pct]
    z_score = calc_z_score(window)
    level = describe_z(z_score, multiplier)

    msg = (f"今日（{today}）纳斯达克综合指数收于 {latest_close:.2f} 点，"
           f"较前一交易日{direction} {abs(change):.2f} 点，涨跌幅 {pct:+.2f}%。\n"
           f"异常度 Z = {z_score:.2f}（{level}）")
    return msg, pct, today, latest_close, change, z_score

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
    config = load_config()
    multiplier = config["sensitivity_multiplier"]
    msg, pct, today, close, change, z_score = get_today_data(multiplier)
    print(msg)

    records = load_history()
    if not records or records[-1][0] != today:
        fetch_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        records.append((today, close, change, pct, z_score, fetch_time))
        save_history(records)
        print(f">> 已记录 {today} 数据")

    send_email(f"【纳斯达克收盘】{today} 涨跌幅 {pct:+.2f}%", msg)
    print(">> 邮件已发送")
