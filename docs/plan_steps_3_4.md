# IXIC 智能体演进 — 第三步 & 第四步详细规划

---

## 第三步：主动规划

### 核心理念
脚本不再等用户指令，而是自己判断市场状态并决定下一步行动。

### 状态机

```
       第1天跌 → 正常发邮件
       第2天跌 → 正常发
       第3天跌 → "连续3天了"
            ↓ 进入 abnormal 状态
            ↓ 抓当天 NASDAQ 新闻
            ↓ 邮件正文末尾追加新闻摘要
       第4天跌 → "还在跌"
            ↓ 算近 3 个月最大回撤
            ↓ 邮件标题加 [异常时段]
       第5天跌 → 邮件强化异常标记
            ↓
       某天涨了 → "好了，恢复 normal"
            ↓ 发一封"异常时段结束"邮件
```

### 新增文件

#### 1. `market_state.json`

```json
{
  "state": "normal",
  "consecutive_drops": 0,
  "abnormal_since": null,
  "max_drawdown_3m": null
}
```

状态值：`"normal"` | `"abnormal"`

#### 2. `fetch_news.py`

功能：
- 用 requests 抓 RSS 源（推荐：Yahoo Finance RSS / Google News）
- 解析当天 NASDAQ 相关新闻标题 + 链接
- 返回前 3 条

免费 RSS 源示例：
- `https://finance.yahoo.com/news/rssindex`
- `https://news.google.com/rss/search?q=NASDAQ&hl=en-US&gl=US&ceid=US:en`

依赖：`feedparser` 或直接用 `requests` + `xml.etree.ElementTree`（标准库）

#### 3. `calc_drawdown.py`

功能：
- 读 `history.csv`
- 取最近 3 个月数据
- 算最大回撤 = max(从峰值到谷底的跌幅)
- 返回最大回撤百分比

公式：`max_drawdown = min((close - peak) / peak)` 在窗口期内

### 修改 `nasdaq.py`（__main__ 部分）

伪代码逻辑：

```
每天收盘后:
  判断今天涨跌
  更新 consecutive_drops
  
  if consecutive_drops >= 3:
    状态 = abnormal
    新闻 = fetch_news()
    邮件正文追加新闻
    
  if consecutive_drops >= 5:
    回撤 = calc_drawdown()
    邮件标题加 [异常时段] + 回撤数据
    
  if 今天涨了 and 状态 == abnormal:
    状态 = normal
    consecutive_drops = 0
    发"异常结束"邮件
    
  保存 market_state.json
```

### 邮件变化示例

```
正常日：
  标题：【纳斯达克收盘】2026-06-10 涨跌幅 +0.50%
  正文：今日收于... Z=0.32（正常波动）

连跌3天：
  标题：【纳斯达克收盘】2026-06-10 涨跌幅 -1.20%
  正文：今日收于... Z=-1.89（值得注意）
  ────
  📰 今日相关新闻：
  1. NASDAQ sinks as tech stocks tumble
  2. Fed rate decision weighs on market

连跌5天：
  标题：【异常时段】纳斯达克连跌5天，近3月最大回撤 -8.3%
  正文：...
  ────
  📰 今日相关新闻：
  ...
  📉 近3月最大回撤：-8.3%（发生在 2026-06-08）
```

### 工作流改动

`daily.yml` 加一步提交 `market_state.json`：

```yaml
- run: |
    git add history.csv market_state.json
    git diff --cached --quiet || git commit -m "daily: update data"
    git push
```

---

## 第四步：长期记忆

### 核心理念
从"只看过去 20 天"进化到"记住所有历史模式，遇到类似情况能参考过去经验"。

### 什么是"记忆"

每次触发异常（Z ≥ 值得注意），系统自动记录一条记忆：

```json
{
  "date": "2026-06-10",
  "trigger": "Z=-2.1",
  "consecutive_drops": 3,
  "close": 18500.00,
  "change_pct": -1.8,
  "state": "abnormal",
  "lasted_days": 4,
  "recovery": {
    "next_5d_pct": 2.3,
    "took_to_recover_days": 3
  }
}
```

### 新增文件

#### `memory.json`

存储所有异常事件的完整记录。结构：

```json
{
  "events": [
    { ... 上述记录 },
    { ... 下一条 }
  ],
  "performance": {
    "avg_z_when_abnormal": -2.3,
    "avg_drop_during_abnormal": -4.1,
    "avg_recovery_days": 3.2
  }
}
```

### 核心逻辑

两个时间点记录：

**异常发生时（当天）**：
```
触发异常 → 记一条记忆（填 trigger、consecutive_drops、close、change_pct）
```

**异常结束后（恢复 normal 时）**：
```
回填该次异常：
  - lasted_days: 持续了几天
  - recovery.next_5d_pct: 结束后 5 天涨跌幅
  - recovery.took_to_recover_days: 几天回到异常前价格
更新 performance 统计数据
```

### 查询历史模式

下次再触发异常时，查 memory 里类似情况：

```
当前 Z=-2.0，连跌 3 天
    ↓
查 memory：历史上 Z<=-2.0 且 连跌>=3 天的记录
    ↓
如果有：
  平均后续 5 天涨跌 = X%
  平均持续天数 = Y 天
  平均恢复天数 = Z 天
    ↓
邮件追加一句话：
  📋 历史参考：过去 N 次类似情况（Z≤-2.0+连跌3天），
     平均后续5天再跌 X%，平均持续 Y 天后恢复
```

### 修改 `nasdaq.py`

新增函数：

| 函数 | 作用 |
|------|------|
| `load_memory()` | 读 memory.json |
| `save_memory(memory)` | 写 memory.json |
| `record_abnormal_event(z, drops, close, pct)` | 异常时存草稿 |
| `finalize_abnormal_event(end_date)` | 恢复时回填 recovery |
| `query_similar_patterns(z, drops)` | 查历史相似模式 |
| `build_memory_advice(z, drops)` | 组装"历史参考"文本 |

### 在邮件中的呈现

```
今日（2026-06-10）纳斯达克综合指数收于 18300.00 点，
较前一交易日📉 跌 250.00 点，涨跌幅 -1.35%。
异常度 Z = -2.10（值得注意）

📋 历史参考：过去 4 次 Z≤-2.0 且连跌≥3 天的情况中，
   平均后续 5 天再跌 1.8%，异常平均持续 3.5 天。
```

### 不需要新依赖

全部用 `json` 标准库操作，不需要额外 pip install。

### 数据积累的进化

| 运行时间 | memory 数据量 | 参考准确度 |
|---------|-------------|-----------|
| 1 个月 | 3-5 条 | 粗略 |
| 6 个月 | 20-30 条 | 有参考价值 |
| 1 年+ | 50+ 条 | 统计意义明显 |

系统越跑越聪明，不需要你改任何代码。

---

## 四步总览

| 步骤 | 核心 | 用户参与 | 智能程度 |
|------|------|---------|---------|
| **1. 自适应** | Z-score 算阈值 | 无 | 低级 |
| **2. 反馈闭环** | Issue 调敏感度 | 主动反馈 | 中级 |
| **3. 主动规划** | 连跌自动查新闻算回撤 | 无需参与 | 高级 |
| **4. 长期记忆** | 记录历史，参考过去 | 无需参与 | 高级+ |
