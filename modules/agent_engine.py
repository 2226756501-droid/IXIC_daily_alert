"""AI Agent engine using OpenAI Agents SDK with DeepSeek V4 Flash."""

import logging
import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_agent: Any = None
_runner: Any = None


def get_deepseek_api_key() -> str:
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        logger.warning("DEEPSEEK_API_KEY 未配置")
    return key


def is_available() -> bool:
    return bool(get_deepseek_api_key())


def _build_agent() -> tuple[Any, Any]:
    from agents import (
        Agent,
        OpenAIChatCompletionsModel,
        AsyncOpenAI,
        Runner,
        function_tool,
    )

    api_key = get_deepseek_api_key()
    base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    client = AsyncOpenAI(base_url=base_url, api_key=api_key)

    model = OpenAIChatCompletionsModel(
        model="deepseek-v4-flash",
        openai_client=client,
    )

    @function_tool
    def get_today_data() -> str:
        """获取今日纳斯达克指数数据，包括收盘价、涨跌幅、Z-score"""
        from modules.data_fetcher import get_today_data as _get
        from modules.storage import load_config

        config = load_config()
        multiplier = config.get("sensitivity_multiplier", 1.0)
        msg, _pct, _date, _close, _change, _z, _open, _high, _low, _volume = _get(multiplier)
        return msg

    @function_tool
    def get_history_summary(days: int = 30) -> str:
        """获取最近 N 天的纳斯达克历史数据摘要，包含每日涨跌幅和Z-score"""
        from modules.storage import load_history

        records = load_history()
        if not records:
            return "暂无历史数据"

        recent = records[-days:]
        total = len(recent)
        avg_pct = sum(r.pct for r in recent) / total
        max_pct = max(r.pct for r in recent)
        min_pct = min(r.pct for r in recent)
        dates = f"{recent[0].date} ~ {recent[-1].date}"

        return (
            f"最近 {total} 天（{dates}）：\n"
            f"- 平均涨跌幅：{avg_pct:+.2f}%\n"
            f"- 最大涨幅：{max_pct:+.2f}%\n"
            f"- 最大跌幅：{min_pct:+.2f}%\n"
            f"- 最新 Z-score：{recent[-1].z_score:.2f}"
        )

    @function_tool
    def get_today_news() -> str:
        """获取今日纳斯达克相关新闻标题"""
        from modules.news_fetcher import fetch_nasdaq_news

        news = fetch_nasdaq_news()
        if not news:
            return "暂无相关新闻"
        return "\n".join(f"- {n}" for n in news)

    @function_tool
    def get_market_state() -> str:
        """获取当前市场状态：是否异常时段、连跌天数等"""
        from modules.storage import load_market_state

        state = load_market_state()
        s = state.get("state", "normal")
        drops = state.get("consecutive_drops", 0)
        since = state.get("abnormal_since", None)
        dd = state.get("max_drawdown_3m", None)

        lines = [f"状态：{'异常' if s == 'abnormal' else '正常'}"]
        lines.append(f"连续下跌天数：{drops}")
        if since:
            lines.append(f"异常开始日期：{since}")
        if dd:
            lines.append(f"近3月最大回撤：{dd.get('max_drawdown_pct', 'N/A')}%（{dd.get('date', 'N/A')}）")
        return "\n".join(lines)

    @function_tool
    def get_memory_events() -> str:
        """获取历史异常事件记录，含每次异常的触发Z值、持续天数等"""
        from modules.storage import load_memory

        mem = load_memory()
        events = mem.get("events", [])
        if not events:
            return "暂无异常事件记录"

        lines = [f"共 {len(events)} 次异常事件："]
        for e in events[-5:]:
            lasted = e.get("lasted_days", "进行中")
            lines.append(
                f"- {e.get('date', '?')} Z={e.get('trigger_z', '?'):.1f} "
                f"连跌{e.get('consecutive_drops', '?')}天 "
                f"持续{lasted}天 "
                f"收{e.get('close', '?'):.0f} "
                f"涨跌{e.get('change_pct', '?'):+.2f}%"
            )
        return "\n".join(lines)

    agent = Agent(
        name="NASDAQ Analyst",
        instructions=(
            "你是纳斯达克智能分析助手。你用中文回答，回答要简洁有数据支撑。\n\n"
            "可用工具：\n"
            "- get_today_data：获取今日数据\n"
            "- get_history_summary：获取最近N天历史摘要\n"
            "- get_today_news：获取今日新闻\n"
            "- get_market_state：获取市场状态\n"
            "- get_memory_events：获取历史异常事件\n\n"
            "根据用户问题选择合适的工具。如果用户问综合性问题，可以调用多个工具。"
        ),
        model=model,
        tools=[
            get_today_data,
            get_history_summary,
            get_today_news,
            get_market_state,
            get_memory_events,
        ],
    )

    return agent, Runner


def generate_email(ctx: dict[str, Any]) -> tuple[str, str] | None:
    """Generate email subject and body using AI.
    Returns (subject, body) or None if unavailable or fails.
    """
    if not is_available():
        return None

    prompt: str = _build_email_prompt(ctx)

    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=get_deepseek_api_key(),
            base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )
        response = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600,
            temperature=0.7,
        )
        text: str = response.choices[0].message.content.strip()
        lines: list[str] = text.split("\n", 1)
        subject: str = lines[0].strip().rstrip(".")
        body: str = lines[1].strip() if len(lines) > 1 else ""
        if len(subject) > 60:
            subject = subject[:57] + "..."
        return subject, body
    except Exception as e:
        logger.warning("AI 邮件生成失败: %s", e)
        return None


def _build_email_prompt(ctx: dict[str, Any]) -> str:
    lines: list[str] = [
        "你是一名专业的金融编辑。请根据以下数据生成一封纳斯达克日报邮件。",
        "",
        "【今日数据】",
        ctx["msg"],
        "",
        f"【市场状态】{'异常' if ctx.get('state') == 'abnormal' else '正常'}",
        f"连跌天数: {ctx.get('drops', 0)}",
    ]
    if ctx.get("regime"):
        lines.append(f"波动率环境: {ctx['regime']} {ctx.get('regime_note', '')}")
    if ctx.get("vol_ratio") and ctx["vol_ratio"] > 0:
        vol_note: str = "（显著放量）" if ctx["vol_ratio"] > 1.5 else "（缩量）" if ctx["vol_ratio"] < 0.5 else ""
        lines.append(f"量能比: {ctx['vol_ratio']} {vol_note}")
    if ctx.get("drawdown"):
        dd: dict[str, Any] = ctx["drawdown"]
        lines.append(f"近3月最大回撤: {dd['max_drawdown_pct']}% ({dd['date']})")
    if ctx.get("recovery"):
        lines.append(f"今日异常时段结束，连跌{ctx['drops']}天后恢复")
    if ctx.get("news"):
        lines.append("")
        lines.append("【相关新闻】")
        for h in ctx["news"]:
            lines.append(f"- {h}")
    if ctx.get("advice"):
        lines.append("")
        lines.append(f"【历史参考】{ctx['advice']}")

    # Recent feedback summary
    try:
        from modules.storage import load_feedback
        fb: list[dict[str, str]] = load_feedback()
        if fb:
            recent_fb: list[dict[str, str]] = fb[-5:]
            satisfied: int = sum(1 for f in recent_fb if f.get("rating") == "1")
            dissatisfied: int = sum(1 for f in recent_fb if f.get("rating") == "2")
            total_fb: int = satisfied + dissatisfied
            if total_fb >= 3:
                lines.append("")
                lines.append(f"【近期用户反馈】最近{total_fb}次反馈中，满意{satisfied}次，不满意{dissatisfied}次")
                if dissatisfied > satisfied:
                    lines.append("提示：用户对近期邮件风格不满意，请调整为更简洁、数据更突出的风格。")
    except Exception:
        pass

    lines.extend([
        "",
        "【格式要求】",
        "第一行作为邮件标题，不超过50个字",
        "空一行后开始正文",
        "正文用中文，专业但易懂，包含数据分析与市场解读",
        "正文开头先写几个字概括今日走势，如\"小幅收涨\"\"明显回调\"",
        "如果有异常信息，在正文中突出说明",
        "正文最后一段写综合判断与建议",
    ])
    return "\n".join(lines)


def chat(query: str, history: list[dict[str, str]] | None = None) -> str:
    if not is_available():
        return "⚠️ AI 功能未配置：请设置 DEEPSEEK_API_KEY"

    global _agent, _runner
    if _agent is None or _runner is None:
        _agent, _runner = _build_agent()

    try:
        messages = []
        if history:
            for msg in history[-10:]:
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": query})

        result = _runner.run_sync(_agent, messages)
        return result.final_output
    except Exception as e:
        logger.error("Agent 调用失败: %s", e)
        return f"⚠️ AI 分析暂时不可用（{e}）"
