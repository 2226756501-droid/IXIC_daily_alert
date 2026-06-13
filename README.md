# 📊 NASDAQ 智能监控系统

全自动 NASDAQ 指数监控 + 异常检测 + 数据可视化仪表盘。

[![Streamlit App](https://img.shields.io/badge/Streamlit-Deployed-brightgreen)](https://ixic-daily-alert.streamlit.app)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Automated-orange)

---

## ✨ 功能

| 功能 | 说明 |
|------|------|
| **📈 实时行情** | 自动从 Yahoo Finance 获取 NASDAQ 每日数据 |
| **🔍 异常检测** | 基于 Z-score 的智能异常识别 |
| **🤖 自动化运行** | GitHub Actions 每天自动采集、分析、推送 |
| **📧 邮件告警** | 连跌时自动发送邮件并附新闻摘要 |
| **📊 可视化仪表盘** | 交互式图表（走势、Z-score、回撤、统计分布） |
| **🧠 长期记忆** | 记录每次异常事件，历史参考辅助判断 |
| **📰 RSS 新闻** | 自动抓取 NASDAQ 相关新闻 |

## 🖼️ 预览

![Dashboard](https://img.shields.io/badge/📊-Live_Dashboard-blue?style=for-the-badge)

👉 **在线体验**: [ixic-daily-alert.streamlit.app](https://ixic-daily-alert.streamlit.app)

## 🗂️ 项目结构

```
ixic/
├── app.py                        # Streamlit 网页仪表盘
├── nasdaq.py                     # CLI 入口（日常运行）
├── requirements.txt              # Python 依赖
├── Dockerfile                    # 容器化部署
├── .env.example                  # 环境变量模板
│
├── modules/
│   ├── __init__.py
│   ├── data_fetcher.py           # Yahoo Finance 数据获取
│   ├── analyzer.py               # Z-score 计算 & 异常检测
│   ├── news_fetcher.py           # RSS 新闻抓取
│   ├── visualizer.py             # Plotly 图表生成
│   ├── drawdown.py               # 最大回撤计算
│   ├── config.py                 # 环境变量配置
│   └── holidays.py               # 美股休市日历
│
├── .github/workflows/
│   └── daily.yml                 # 每日自动运行工作流
└── docs/
    └── 项目详细介绍.md
```

## 🚀 快速开始

### 本地运行

```bash
git clone https://github.com/2226756501-droid/IXIC_daily_alert.git
cd IXIC_daily_alert

# 可选：创建虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动网页仪表盘
streamlit run app.py
```

### Docker 运行

```bash
docker build -t ixic-monitor .
docker run -p 8501:8501 ixic-monitor
```

### 配置邮件告警

```bash
cp .env.example .env
# 编辑 .env 填写邮箱信息
```

## ⚙️ 技术栈

| 技术 | 用途 |
|------|------|
| Python 3.12 | 核心语言 |
| Streamlit | Web 仪表盘 |
| Plotly | 交互式图表 |
| Pandas | 数据处理 |
| Prophet (可选) | 时序预测 |
| GitHub Actions | CI/CD + 定时任务 |
| Docker | 容器化部署 |

## 📈 数据流

```
Yahoo Finance API → history.csv → GitHub Actions (每日更新)
                                        ↓
                          GitHub Raw (数据源) ←→ Streamlit Cloud (网页)
                                        ↓
                              邮件告警 (异常时推送)
```

## 📄 许可证

MIT
