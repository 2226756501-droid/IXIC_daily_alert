# IXIC NASDAQ 智能监控系统 — 完整介绍

## 一、项目概述

这是一个**全自动的纳斯达克指数监控智能体**，每天自动获取收盘数据，计算异常程度，根据连续涨跌天数自动决策（发邮件、查新闻、算回撤），并记录异常事件形成长期记忆。

**一句话：** 一个能自主感知、决策、行动、记忆的迷你 AI Agent。

---

## 二、架构图

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  感知     │ →  │  决策     │ →  │  行动     │ →  │  记忆     │
│ (拿数据)  │    │ (算/判断)  │    │ (发邮件等) │    │ (存经验)  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
     │               │               │               │
     ↓               ↓               ↓               ↓
 Yahoo API      Z-score 算异常    SMTP 发邮件     memory.json
                状态机判阶段      GitHub 提交      history.csv
                连跌计数          RSS 抓新闻       market_state.json
                                 算最大回撤
```

---

## 三、每份文件的作用

### 1. `nasdaq.py`（核心文件，276行）

整个智能体的大脑。包含：

#### 感知层

| 函数 | 作用 | 通俗理解 |
|------|------|---------|
| `fetch_chart(range)` | 调 Yahoo Finance API 拿 NASDAQ 收盘价 | 每天去查价格 |
| `get_today_data()` | 获取最新收盘价、算涨跌幅、算 Z-score | 算出今天跌了多少、是否异常 |
| `init_history()` | 首次运行时拉5年历史数据初始化 | 第一次用的时候造历史记录 |

#### 决策层

| 函数 | 作用 | 通俗理解 |
|------|------|---------|
| `calc_z_score(pcts)` | 计算 Z-score（当前涨跌幅和过去20天比有多异常） | 看今天跌得是不是反常 |
| `describe_z(z)` | 把 Z-score 转成中文描述 | 正常/值得注意/显著异常/极端 |
| 主逻辑状态机 | 根据连续下跌天数决定行为 | 第3天干什么、第4天干什么 |

**Z-score 计算公式（面试重点）：**

```
Z = (今日涨跌幅 - 过去19天平均涨跌幅) / 过去19天标准差
```

- Z = 0 → 和平时一样
- Z = -2 → 比平时低了2个标准差，属于"显著异常"
- Z = -3 → 极端行情

简单理解：**过去20天里，今天的跌幅有多不寻常。**

#### 行动层

| 函数 | 作用 | 通俗理解 |
|------|------|---------|
| `send_email()` | 通过 SMTP 发邮件 | 发通知到邮箱 |
| `fetch_nasdaq_news()`（跨文件） | 从 Yahoo/Google RSS 抓 NASDAQ 相关新闻 | 连跌时自动搜新闻 |
| `calc_max_drawdown_3m()`（跨文件） | 算近3个月最大回撤 | 看这波下跌有多深 |

#### 记忆层

| 函数 | 作用 | 通俗理解 |
|------|------|---------|
| `record_abnormal()` | 异常发生时写入 memory.json | 记录这次异常事件 |
| `finalize_abnormal()` | 异常结束时回填持续天数 | 记录这次异常持续了几天 |
| `query_similar()` | 查历史上相似情况 | 以前这种跌法后续怎么走的 |
| `build_memory_advice()` | 组装"历史参考"文本加到邮件 | 邮件里多一句"历史参考" |

### 2. `adjust_threshold.py`（反馈闭环，42行）

接收 GitHub Issue 中的关键词（"提高敏感度"/"降低敏感度"），调整 `threshold_config.json` 中的倍率，下次运行生效。

这就是**反馈闭环**——用户可以在 GitHub 上提 Issue 说"太敏感了"，系统自动调参数。

### 3. `fetch_news.py`（新闻抓取，32行）

从 Yahoo Finance RSS 和 Google News RSS 抓取标题含 "nasdaq" 的新闻，返回最多3条。

### 4. `calc_drawdown.py`（回撤计算，53行）

读 `history.csv` 取近3个月数据，算出从峰值跌到谷底的最大百分比。

公式：`最大回撤 = min((当日价格 - 期间最高价) / 期间最高价)`

### 5. `.github/workflows/daily.yml`（自动化调度）

每天 21:30 UTC（北京时间凌晨5:30）自动运行 `nasdaq.py`，执行完整流程并提交数据。

### 6. `.github/workflows/feedback.yml`（自动化反馈）

当有人提 Issue 或评论 Issue 时自动触发，运行 `adjust_threshold.py` 调整参数。

### 7. `market_state.json`（状态文件）

手写的一个极简状态机：

```
normal →（连跌3天）→ abnormal →（涨了）→ normal
```

记录当前状态、连续下跌天数、异常开始日期、近3月最大回撤。

### 8. `history.csv`（历史数据）

每天追加一行：日期、收盘价、涨跌额、涨跌幅、Z-score、获取时间。

### 9. `threshold_config.json`（阈值配置）

```json
{"sensitivity_multiplier": 1.0}
```

倍率 = 1.0 就是标准阈值。调高=更不敏感（少报警），调低=更敏感（多报警）。

### 10. `memory.json`（长期记忆）

每次异常触发时写一条记录，异常结束时回填。格式：

```json
{
  "events": [
    {
      "id": 1,
      "date": "2026-06-10",
      "trigger_z": -2.1,
      "consecutive_drops": 3,
      "close": 25169.50,
      "change_pct": -1.98,
      "lasted_days": null,
      "recovery_date": null
    }
  ]
}
```

---

## 四、完整运行流程（面试时按这个顺序讲）

```
每一天自动运行：
  1. init_history()  →  如果 history.csv 不存在，拉5年数据初始化
  2. get_today_data() →  调 Yahoo API 拿最新收盘价、算涨跌幅、算 Z-score
  3. 如果今天有新数据 → 追加到 history.csv
  4. 判断涨跌：
     ├── 跌了 → consecutive_drops +1
     │   ├── 第3次跌 → 标记 abnormal、抓新闻、记录记忆
     │   ├── 第4次+ → 算近3月最大回撤、改邮件标题
     │   └── 如果 Z≤-1.5 → 查历史记忆，追加参考建议
     └── 涨了 → 如果在 abnormal 状态 → 恢复 normal、完结记忆
  5. 发邮件
  6. 数据自动 commit & push 到 GitHub
```

---

## 五、面试可以怎么介绍（逐字稿参考）

**"介绍你的 IXIC 项目"**

> 这是一个全自动的纳斯达克指数监控系统。它每天定时从 Yahoo Finance 获取收盘数据，用 Z-score 算法判断涨跌幅是否异常，然后根据一个简单的状态机自动决策：
>
> - 正常日：发一封普通邮件告知收盘数据
> - 连跌3天：自动抓取当天 NASDAQ 新闻附在邮件里，并记录异常事件
> - 连跌4天以上：自动计算近3个月最大回撤，邮件标题改为"异常时段"
> - 哪天涨了：如果是异常状态中首次上涨，自动结束异常状态，发恢复通知
>
> 此外还有一个反馈闭环：用户可以在 GitHub Issue 里写"提高敏感度"或"降低敏感度"，系统会自动调整阈值参数，下次生效。
>
> 最后还有一个长期记忆功能：每次异常事件会被记录下来，后续出现类似行情时，系统会查历史数据并在邮件中说"过去几次类似情况平均持续 X 天"。

**"为什么用 Z-score 而不是固定阈值"**

> 固定阈值（比如跌2%就报警）不适应市场变化。牛市波动大、熊市波动小，固定阈值要么漏报要么误报。Z-score 是看"今天的涨跌幅相对于过去20天有多不寻常"，市场波动大时阈值自动放宽，波动小时自动收紧，不需要人工调。

**"你碰到过什么问题"**

> 最开始用的 range=5d 和 range=1mo 拉 Yahoo 数据，发现返回的只是已完成的日线，不含当天的收盘。后来改成 range=1d，用 API 返回的 regularMarketPrice 拿当天价格、meta.ChartPreviousClose 拿前收盘才算准。

---

## 六、项目亮点总结

| 类别 | 亮点 |
|------|------|
| 自动化 | GitHub Actions 定时运行，无人值守 |
| 智能 | Z-score 自适应阈值，不依赖固定数值 |
| 闭环 | 用户提 Issue 就能调参数 |
| 记忆 | 异常事件自动记录，历史可查 |
| 容错 | 多种 fallback（API 挂了用本地缓存、正则解析多个日期格式） |
| 状态机 | 轻量级状态管理，无外部依赖 |

---

## 七、技术栈

| 模块 | 技术 |
|------|------|
| 语言 | Python 3.12 |
| 数据源 | Yahoo Finance API (REST) |
| 新闻源 | Yahoo RSS / Google News RSS |
| 通知 | SMTP (QQ邮箱) |
| 自动化 | GitHub Actions (CI/CD) |
| 数据存储 | CSV + JSON（无数据库） |
| 第三方依赖 | 仅 requests |

**不依赖任何 ML 框架（PyTorch/TensorFlow/Scikit-learn），Z-score 纯手算。**

---

## 八、项目结构一览

```
D:\ixic/
│
├── nasdaq.py                  → 核心智能体（感知+决策+行动+记忆）
├── adjust_threshold.py         → 反馈闭环（Issue 调参）
├── fetch_news.py               → RSS 新闻抓取
├── calc_drawdown.py            → 最大回撤计算
├── history.csv                 → 日线历史数据库
├── market_state.json           → 状态机文件
├── threshold_config.json       → 阈值配置
├── memory.json                 → 长期记忆（异常事件记录）
├── plan_steps_3_4.md           → 架构设计文档
├── README.md                   → 使用说明
│
└── .github/workflows/
    ├── daily.yml               → 每日自动运行
    └── feedback.yml            → Issue 反馈自动响应
```
