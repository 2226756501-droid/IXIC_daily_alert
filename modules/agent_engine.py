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
        from modules.data_fetcher import get_today_data as _get, load_config

        config = load_config()
        multiplier = config.get("sensitivity_multiplier", 1.0)
        msg, _pct, _date, _close, _change, _z = _get(multiplier)
        return msg

    @function_tool
    def get_history_summary(days: int = 30) -> str:
        """获取最近 N 天的纳斯达克历史数据摘要，包含每日涨跌幅和Z-score"""
        from modules.data_fetcher import load_history

        records = load_history()
        if not records:
            return "暂无历史数据"

        recent = records[-days:]
        total = len(recent)
        avg_pct = sum(r[3] for r in recent) / total
        max_pct = max(r[3] for r in recent)
        min_pct = min(r[3] for r in recent)
        dates = f"{recent[0][0]} ~ {recent[-1][0]}"

        return (
            f"最近 {total} 天（{dates}）：\n"
            f"- 平均涨跌幅：{avg_pct:+.2f}%\n"
            f"- 最大涨幅：{max_pct:+.2f}%\n"
            f"- 最大跌幅：{min_pct:+.2f}%\n"
            f"- 最新 Z-score：{recent[-1][4]:.2f}"
        )

    @function_tool
    def get_today_news() -> str:
        """获取今日纳斯达克相关新闻标题"""
        from modules.news_fetcher import fetch_nasdaq_news

        news = fetch_nasdaq_news(max_items=5)
        if not news:
            return "暂无相关新闻"
        return "\n".join(f"- {n}" for n in news)

    @function_tool
    def get_market_state() -> str:
        """获取当前市场状态：是否异常时段、连跌天数等"""
        from modules.data_fetcher import load_market_state

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
        from modules.data_fetcher import load_memory

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
