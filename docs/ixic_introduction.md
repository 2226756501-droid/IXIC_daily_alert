# 📊 NASDAQ 智能监控系统 — 项目介绍

## 一、一句话介绍

这是一个**全自动的纳斯达克指数监控系统**，每天自动获取数据、分析异常、发邮件通知，并配有网页仪表盘随时查看。

---

## 二、项目结构

```
D:\ixic/
│
├── nasdaq.py               ← 🤖 核心智能体（数据采集+分析+决策+邮件）
├── app.py                  ← 🌐 网页仪表盘（Streamlit）
├── adjust_threshold.py     ← ⚙️ GitHub Issue 调参
│
├── modules/
│   ├── stats.py            ← 📊 Z-score 计算、异常描述
│   ├── analyzer.py         ← 🧠 异常事件记录、记忆管理
│   ├── data_fetcher.py     ← 📡 Yahoo Finance 数据获取
│   ├── visualizer.py       ← 📈 Plotly 图表
│   ├── news_fetcher.py     ← 📰 RSS 新闻抓取
│   ├── drawdown.py         ← 📉 最大回撤计算
│   ├── holidays.py         ← 📅 美股休市日历
│   └── config.py           ← ⚙️ 邮箱配置
│
├── .github/workflows/
│   ├── daily.yml           ← ⏰ 每天自动运行
│   ├── test.yml            ← ✅ 每次 push 自动测试
│   └── feedback.yml        ← 💬 Issue 调参
│
├── history.csv             ← 💾 每日行情数据库
├── market_state.json       ← 🔄 当前状态（正常/异常）
├── memory.json             ← 🧠 长期记忆（异常事件）
├── threshold_config.json   ← 🎛️ 敏感度配置
│
├── tests/                  ← 🧪 47 个 pytest 测试
├── Dockerfile              ← 🐳 多阶段构建
└── docs/                   ← 📄 文档
```

---

## 三、运行流程

```
每天自动运行：

1️⃣ 获取数据 → Yahoo Finance API
2️⃣ 计算指标 → 涨跌幅、Z-score
3️⃣ 状态判断 → 跌了？第几天？
4️⃣ 执行动作 → 发邮件、抓新闻、算回撤
5️⃣ 记录记忆 → 异常事件存 memory.json
6️⃣ 提交数据 → git commit + push
```

| 连跌天数 | 系统行为 |
|---------|---------|
| 第 1-2 天 | 普通邮件：今日收盘数据 |
| 第 3 天 | 标记异常 + 抓取 NASDAQ 新闻 + 记录事件 |
| 第 4 天+ | 算近 3 月最大回撤 + 改邮件标题 |
| 恢复上涨 | 完结异常事件 + 发恢复通知 |

---

## 四、关键技术点

### Z-score（异常检测核心）

```
Z = (今日涨跌幅 - 过去19天平均涨跌幅) ÷ 过去19天标准差
```

| Z 范围 | 含义 |
|--------|------|
| \|Z\| < 1 | 正常波动 |
| 1 ≤ \|Z\| < 2 | 值得注意 |
| 2 ≤ \|Z\| < 3 | 显著异常 |
| \|Z\| ≥ 3 | 极端行情 |

只依赖最近 20 个交易日（LOOKBACK=20），不累积全部历史，确保灵敏。

### 状态机（决策核心）

```
normal ──(连跌3天)──→ abnormal ──(上涨)──→ normal
```

用 `market_state.json` 记录：当前状态、连跌天数、异常起始日、近 3 月最大回撤。

### 容错机制

| 故障场景 | 保护措施 |
|---------|---------|
| Yahoo API 挂了 | 用本地 history.csv 缓存 |
| GitHub raw 挂了 | 用本地 cache/ 文件夹缓存 |
| 邮箱未配置 | 跳过发送，不崩溃 |
| 数据文件不存在 | 自动用默认值初始化 |

---

## 五、自动化与 CI/CD

| Workflow | 触发时机 | 做的事 |
|---------|---------|--------|
| daily.yml | 工作日 21:30 UTC | 采集数据→分析→发邮件→提交 |
| test.yml | 每次 push / PR | 跑全部 47 个测试 |
| feedback.yml | Issue / 评论 | 根据关键词调敏感度 |

---

## 六、网页仪表盘

地址：https://ixic-daily-alert.streamlit.app

功能：
- 顶部 4 个核心指标：指数、涨跌幅、Z-score、连跌天数
- 近 90 日行情走势（异常点标红）
- Z-score 异常检测柱状图（红线联动灵敏度）
- 回撤分析、统计分布、月度/周度对比
- NASDAQ 相关新闻
- 历史异常事件记录表

---

## 七、技术栈

| 技术 | 用途 |
|------|------|
| Python 3.12 | 核心语言 |
| Streamlit | 网页仪表盘 |
| Plotly | 交互式图表 |
| GitHub Actions | CI/CD + 定时任务 |
| Docker | 容器化部署 |
| Yahoo Finance API | 数据源 |
| SMTP (QQ邮箱) | 邮件通知 |

第三方依赖仅 5 个：streamlit、pandas、requests、plotly、python-dotenv。**无任何 ML 框架**。

---

## 八、已经做过的改进（共 14 项）

### 第一轮（基础修复）
1. 删除重复定义的函数
2. 修正 2027 劳动节日期错误
3. 统一配置入口（只保留 threshold_config.json）
4. Z-score 固定 20 天回看窗口
5. print → logging 统一日志
6. Yahoo API 异常保护 + 本地缓存回退

### 第二轮（工程提升）
7. 图表阈值红线联动 multiplier
8. 关键词扩展匹配（调参识别更多说法）
9. 消除循环导入（抽出 stats.py）
10. 新增 21 个测试（共 47 个）
11. CI 加 pytest 步骤
12. Docker 多阶段构建（镜像缩小 40%）
13. app.py 本地缓存兜底（GitHub raw 挂了也不白屏）
14. 独立 CI test.yml（每次 push 自动跑测试）

---

## 九、剩余可改进

| 优先级 | 改进项 | 难度 |
|--------|--------|------|
| 中 | 增加即时消息告警（钉钉/Telegram） | ★★☆ |
| 低 | Docker 二次优化（移除 docs/tests） | ★☆☆ |
