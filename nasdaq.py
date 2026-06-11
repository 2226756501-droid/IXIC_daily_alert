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
STATE_FILE = "market_state.json"
MEMORY_FILE = "memory.json"


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
    data = fetch_chart("1d")
    results = data["chart"]["result"][0]
    meta = results["meta"]
    closes = results["indicators"]["quote"][0]["close"]

    latest_close = meta.get("regularMarketPrice")
    if latest_close is None:
        valid = [c for c in closes if c is not None]
        latest_close = valid[-1]
    latest_close = float(latest_close)

    prev_close = float(meta.get("chartPreviousClose", 0))
    if not prev_close:
        valid = [c for c in closes if c is not None]
        prev_close = valid[-2] if len(valid) >= 2 else latest_close

    change = latest_close - prev_close
    pct = change / prev_close * 100
    data_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    direction = "📈 涨" if change >= 0 else "📉 跌"

    records = load_history()
    hist_pcts = [r[3] for r in records]
    window = hist_pcts[-(LOOKBACK - 1):] + [pct]
    z_score = calc_z_score(window)
    level = describe_z(z_score, multiplier)

    msg = (f"纳斯达克指数收于 {latest_close:.2f} 点，"
           f"较前一交易日{direction} {abs(change):.2f} 点，涨跌幅 {pct:+.2f}%。\n"
           f"数据日期 {data_date}，异常度 Z = {z_score:.2f}（{level}）")
    return msg, pct, data_date, latest_close, change, z_score

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


def load_market_state():
    if not os.path.exists(STATE_FILE):
        return {"state": "normal", "consecutive_drops": 0, "abnormal_since": None, "max_drawdown_3m": None}
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_market_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {"events": [], "next_id": 1}
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)


def save_memory(mem):
    with open(MEMORY_FILE, "w") as f:
        json.dump(mem, f, indent=2)


def record_abnormal(z, drops, close, pct, date):
    mem = load_memory()
    mem["events"].append({
        "id": mem["next_id"],
        "date": date,
        "trigger_z": round(z, 2),
        "consecutive_drops": drops,
        "close": round(close, 2),
        "change_pct": round(pct, 2),
        "lasted_days": None,
        "recovery_date": None
    })
    mem["next_id"] += 1
    save_memory(mem)
    print(f">> 异常事件 #{mem['next_id'] - 1} 已记录")


def finalize_abnormal(end_date, total_drops):
    mem = load_memory()
    for evt in reversed(mem["events"]):
        if evt.get("lasted_days") is None:
            evt["lasted_days"] = total_drops
            evt["recovery_date"] = end_date
            save_memory(mem)
            print(f">> 异常事件 #{evt['id']} 已完结（持续 {total_drops} 天）")
            return


def query_similar(z, drops):
    mem = load_memory()
    matched = [e for e in mem["events"]
               if e.get("lasted_days") and e["trigger_z"] <= z and e["consecutive_drops"] >= drops]
    if len(matched) < 2:
        return None
    avg_last = sum(e["lasted_days"] for e in matched) / len(matched)
    avg_change = sum(e["change_pct"] for e in matched) / len(matched)
    return {"count": len(matched), "avg_lasted_days": round(avg_last, 1), "avg_change_pct": round(avg_change, 2)}


def build_memory_advice(z, drops):
    ref = query_similar(z, drops)
    if not ref:
        return ""
    return (f"📋 历史参考：过去 {ref['count']} 次类似情况中（Z≤{z:.1f}，连跌≥{drops} 天），"
            f"异常平均持续 {ref['avg_lasted_days']} 天，当日平均涨跌幅 {ref['avg_change_pct']:+.2f}%。")


if __name__ == "__main__":
    init_history()
    config = load_config()
    multiplier = config["sensitivity_multiplier"]
    msg, pct, data_date, close, change, z_score = get_today_data(multiplier)
    print(msg)

    records = load_history()
    if not records or records[-1][0] != data_date:
        fetch_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        records.append((data_date, close, change, pct, z_score, fetch_time))
        save_history(records)
        print(f">> 已记录 {data_date} 数据")

    state = load_market_state()
    is_down = pct < 0
    body = msg
    subject = f"【纳斯达克数据】{data_date} 涨跌幅 {pct:+.2f}%"

    if is_down:
        state["consecutive_drops"] = state.get("consecutive_drops", 0) + 1
        drops = state["consecutive_drops"]

        if drops == 3 and state.get("state") == "normal":
            state["state"] = "abnormal"
            state["abnormal_since"] = data_date
            record_abnormal(z_score, drops, close, pct, data_date)
            from fetch_news import fetch_nasdaq_news
            news = fetch_nasdaq_news()
            if news:
                body += "\n────\n📰 今日相关新闻：\n" + "\n".join(f"{i+1}. {h}" for i, h in enumerate(news))

        elif drops >= 4:
            from calc_drawdown import calc_max_drawdown_3m
            dd = calc_max_drawdown_3m()
            if dd:
                state["max_drawdown_3m"] = dd
                body += f"\n────\n📉 近3月最大回撤：{dd['max_drawdown_pct']}%（{dd['date']}）"
                subject = f"【异常时段】纳斯达克连跌{drops}天，近3月最大回撤 {dd['max_drawdown_pct']}%"

    else:
        if state.get("state") == "abnormal":
            drops = state.get("consecutive_drops", 0)
            state["state"] = "normal"
            state["abnormal_since"] = None
            state["consecutive_drops"] = 0
            state["max_drawdown_3m"] = None
            finalize_abnormal(data_date, drops)
            body += f"\n────\n✅ 异常时段结束（连跌{drops}天后恢复）"
            subject = f"【纳斯达克数据】异常时段结束 - {data_date} 涨跌幅 {pct:+.2f}%"
        else:
            state["consecutive_drops"] = 0

    save_market_state(state)

    drops = state.get("consecutive_drops", 0)
    if is_down and drops >= 2 and z_score <= -1.5:
        advice = build_memory_advice(z_score, drops)
        if advice:
            body += "\n" + advice

    send_email(subject, body)
    print(">> 邮件已发送")
