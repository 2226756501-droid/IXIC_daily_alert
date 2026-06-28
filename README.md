# IXIC NASDAQ 智能监控系统

自动抓取纳斯达克指数数据，结合 Z-score 异常检测、DeepSeek AI 分析，通过邮件/Webhook 发送日报，并支持反馈闭环与敏感度回测调优。

## 架构

```
Yahoo Finance API ─┬─> yahoo_client.py ──> data_fetcher.py ──> storage.py (CSV/JSON)
                   │                          │
RSS News ──────────┘                          │
                                              ▼
                                        stats.py (Z-score)
                                        analyzer.py (异常事件)
                                        drawdown.py (回撤分析)
                                        agent_engine.py (DeepSeek AI)
                                              │
                                              ▼
                                        mailer.py → SMTP 邮件
                                        webhook.py → 企业微信/钉钉/Slack/Pushover
                                              │
                                              ▼
                                        feedback_checker.py (IMAP 反馈闭环)
```

## 快速开始

### 1. 克隆并安装

```bash
git clone https://github.com/2226756501-droid/IXIC_daily_alert.git
cd IXIC_daily_alert
python -m venv .venv
.venv\Scripts\activate    # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，填入真实值：

```ini
# 邮箱配置（QQ 邮箱）
SMTP_SERVER=smtp.qq.com
SMTP_PORT=465
EMAIL_USER=your_email@qq.com
EMAIL_PASS=your_authorization_code
NOTIFY_EMAIL=receiver@example.com

# DeepSeek AI（选填，不填则使用模板邮件）
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com

# Webhook（选填，不配置则不推送）
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx
WECOM_WEBHOOK_KEY=xxx
DINGTALK_WEBHOOK_TOKEN=xxx
PUSHOVER_USER_KEY=xxx
PUSHOVER_APP_TOKEN=xxx
```

### 3. 运行

```bash
# 手动运行日报
python nasdaq.py

# 启动 Web 仪表盘
streamlit run app.py

# 检查邮件反馈
python check_feedback.py

# 回填历史 OHLC/Volume 数据
python backfill_ohlc.py
```

### 4. GitHub Actions 部署

Fork 或推送后，在仓库 **Settings > Secrets and variables > Actions** 中添加：

| Secret | 说明 |
|--------|------|
| `SMTP_SERVER` | SMTP 服务器地址 |
| `SMTP_PORT` | SMTP 端口（默认 465） |
| `EMAIL_USER` | QQ 邮箱地址 |
| `EMAIL_PASS` | QQ 邮箱授权码（非登录密码） |
| `NOTIFY_EMAIL` | 接收日报的邮箱 |
| `HEALTHCHECKS_UUID` | healthchecks.io UUID（选填，用于外部监控） |

### 5. Streamlit Cloud 部署

在 [share.streamlit.io](https://share.streamlit.io) 连接仓库后，在 **Settings > Secrets** 填入与 GitHub Secrets 相同的内容（格式为 TOML）：

```toml
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = "465"
EMAIL_USER = "your_email@qq.com"
EMAIL_PASS = "your_authorization_code"
NOTIFY_EMAIL = "receiver@example.com"
DEEPSEEK_API_KEY = "sk-xxxxxxxxxxxxxxxx"
```

## 功能说明

### 日报流水线（每日自动执行）

1. **Yahoo Finance 数据抓取** — 获取 `^IXIC` 收盘、OHLC、成交量
2. **Z-score 异常检测** — 基于 20 日滑动窗口计算异常度
3. **状态机管理** — 监测连跌/异常/恢复等状态转换
4. **新闻抓取** — RSS 抓取 NASDAQ 相关新闻
5. **AI 邮件生成** — DeepSeek V4 Flash 生成日报正文
6. **多通道推送** — 邮件 + Webhook（Slack/企业微信/钉钉/Pushover）
7. **反馈闭环** — IMAP 读取 QQ 邮箱回复评分
8. **数据提交** — 自动 commit + push 更新数据文件

### Web 仪表盘（8 个标签页）

| 标签 | 功能 |
|------|------|
| 📈 行情走势 | K 线图、Z-score 异常检测、涨跌幅对比 |
| 📊 统计分析 | 收盘价/涨跌幅分布、月度/周度收益 |
| 📉 回撤分析 | 近 3 月最大回撤可视化 |
| 📰 新闻 | 当日 NASDAQ 相关新闻 |
| ⚙️ 异常事件 | 历史异常事件记录列表 |
| 🤖 AI 分析 | 基于 DeepSeek 的对话式分析助手 |
| 💬 反馈 | 邮件反馈历史 + 满意度提交 |
| 🎯 回测对比 | 敏感度倍率回测评估与最优选择 |

### 敏感度调优

通过回测对比不同 `sensitivity_multiplier`（0.5~3.0）的历史表现，自动推荐最优倍率。在 `threshold_config.json` 中设置：

```json
{"sensitivity_multiplier": 1.0}
```

或者在 GitHub Issue 中评论含"敏感"关键词，GitHub Actions 自动调整（需配置 `feedback.yml`）。

## 环境变量完整列表

| 变量 | 必填 | 说明 |
|------|------|------|
| `SMTP_SERVER` | 是 | SMTP 服务器地址 |
| `SMTP_PORT` | 是 | SMTP 端口 |
| `EMAIL_USER` | 是 | 邮箱账号 |
| `EMAIL_PASS` | 是 | 邮箱授权码 |
| `NOTIFY_EMAIL` | 否 | 接收邮箱（默认同 EMAIL_USER） |
| `DEEPSEEK_API_KEY` | 否 | DeepSeek API 密钥 |
| `DEEPSEEK_BASE_URL` | 否 | DeepSeek API 地址 |
| `SLACK_WEBHOOK_URL` | 否 | Slack Webhook URL |
| `WECOM_WEBHOOK_KEY` | 否 | 企业微信机器人 key |
| `DINGTALK_WEBHOOK_TOKEN` | 否 | 钉钉机器人 access_token |
| `PUSHOVER_USER_KEY` | 否 | Pushover 用户密钥 |
| `PUSHOVER_APP_TOKEN` | 否 | Pushover 应用令牌 |
| `HEALTHCHECKS_UUID` | 否 | healthchecks.io UUID |

## 测试

```bash
pytest tests/ -v
```

## 数据文件

项目跟踪以下数据文件（git 提交以保持云端同步）：

- `history.csv` — 日线历史数据（1272+ 条记录）
- `market_state.json` — 市场状态机
- `memory.json` — 异常事件记忆
- `threshold_config.json` — 敏感度配置
- `feedback.csv` — 用户反馈记录
- `health.json` — 最近运行健康状态
- `uptime.json` — 运行历史/可用率统计

## 延伸方向

- [ ] **多标的支持** — 配置化支持 SPY/QQQ/个股
- [ ] **SQLite 替代 CSV** — 解决写入并发和数据一致性
- [ ] **TradingView Webhook 集成** — 接收警报作为触发源
- [ ] **外部监控增强** — 接入 UptimeRobot / Better Uptime
