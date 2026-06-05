"""
全局时间工具 - 为所有Agent提供时间感知能力
"""
from datetime import datetime, timedelta
from typing import Optional, Literal
import pytz


def get_current_time(
        timezone: str = "Asia/Shanghai",
        format_type: Literal["full", "date", "time", "iso", "timestamp", "search_context"] = "search_context"
) -> dict:
    """
    全局时间获取工具，所有Agent都可以调用

    Args:
        timezone: 时区，默认中国标准时间
        format_type: 返回格式
            - "search_context": 为搜索Agent优化的时间上下文（默认）
            - "full": 完整日期时间
            - "date": 仅日期
            - "time": 仅时间

    Returns:
        dict: 时间信息
    """
    try:
        tz = pytz.timezone(timezone)
        now = datetime.now(tz)
    except:
        now = datetime.now()
        timezone = "local"

    time_info = {
        "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "day_of_week": now.strftime("%A"),
        "day_of_week_cn": ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][now.weekday()],
        "iso_format": now.isoformat(),
        "timestamp": now.timestamp(),
        "timezone": timezone
    }

    # 搜索上下文模式：提供额外的搜索建议
    if format_type == "search_context":
        yesterday = now - timedelta(days=1)
        this_week_start = now - timedelta(days=now.weekday())
        this_month_start = now.replace(day=1)

        time_info["search_suggestions"] = {
            "today": now.strftime("%Y-%m-%d"),
            "yesterday": yesterday.strftime("%Y-%m-%d"),
            "this_week_start": this_week_start.strftime("%Y-%m-%d"),
            "this_week_end": now.strftime("%Y-%m-%d"),
            "this_month": now.strftime("%Y-%m"),
            "this_year": now.strftime("%Y"),
            "days_ago_7": (now - timedelta(days=7)).strftime("%Y-%m-%d"),
            "days_ago_30": (now - timedelta(days=30)).strftime("%Y-%m-%d"),
        }

        # 关键：生成搜索专用的时间上下文提示
        time_info["search_context_prompt"] = f"""
当前时间：{now.strftime('%Y年%m月%d日 %H:%M')}（{time_info['day_of_week_cn']}）

搜索时间映射：
- "现在/目前" → {now.strftime('%Y-%m-%d')}
- "今天" → {now.strftime('%Y-%m-%d')}
- "昨天" → {yesterday.strftime('%Y-%m-%d')}
- "最近/最新" → 过去7天（{time_info['search_suggestions']['days_ago_7']} 至今）
- "本周" → {this_week_start.strftime('%Y-%m-%d')} 至今
- "这个月" → {now.strftime('%Y年%m月')}
- "今年" → {now.strftime('%Y年')}
"""

    return time_info


def format_time_for_agent(agent_type: str) -> str:
    """
    根据不同Agent类型返回定制化的时间信息

    Args:
        agent_type: "search", "neo4j", "general"

    Returns:
        str: 格式化时间字符串
    """
    time_info = get_current_time()

    if agent_type == "search":
        return time_info.get("search_context_prompt", str(time_info))
    elif agent_type == "neo4j":
        # Neo4j查询可能需要特定的时间格式
        return f"当前日期：{time_info['date']}，当前时间戳：{time_info['timestamp']}"
    else:
        return f"当前时间：{time_info['current_time']}"
