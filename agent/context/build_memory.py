"""工作记忆层——进程内缓存 + 滑动窗口 + 语义裁剪

每轮对话后调用 save_turn 写入，build_working_memory 读取。
后续可替换为 Redis 实现分布式存储。
"""

import logging

logger = logging.getLogger(__name__)

# 保留的最大对话轮数
_MAX_TURNS = 5

# 进程内缓存：thread_id → list[{"role": ..., "content": ...}]
_session_store: dict[str, list[dict]] = {}


def save_turn(thread_id: str, user_msg: str, assistant_msg: str):
    """保存一轮对话到历史缓存"""
    if not thread_id or not user_msg or not assistant_msg:
        return
    if thread_id not in _session_store:#对话历史不存在时初始化列表
        _session_store[thread_id] = []
    _session_store[thread_id].append({"role": "user", "content": user_msg})
    _session_store[thread_id].append({"role": "assistant", "content": assistant_msg})
    logger.info("Session %s: 累计 %d 轮", thread_id, len(_session_store[thread_id]) // 2)


def build_working_memory(thread_id: str | None = None) -> list[dict]:
    """滑动窗口——读取最近 N 轮对话历史

    Args:
        thread_id: 会话标识

    Returns:
        list[dict]: 历史消息列表
    """
    if not thread_id:
        return []
    history = _session_store.get(thread_id, [])
    return history[-(_MAX_TURNS * 2):]  #序列切片语法,从倒数第2*N个消息开始正向取所有的消息


def semantic_prune(
    messages: list[dict],
    query: str,
    max_turns: int = 5,
) -> list[dict]:
    """语义裁剪——剔除与当前 query 不相关的历史轮次

    简单策略：保留最近 max_turns 轮，早期历史中仅保留包含
    query 关键词的轮次。

    Args:
        messages: 完整消息列表（含 system）
        query: 当前用户问题
        max_turns: 最近保留的完整轮数

    Returns:
        list[dict]: 裁剪后的消息列表
    """
    system_msgs = [m for m in messages if m["role"] == "system"]
    dialog_msgs = [m for m in messages if m["role"] != "system"]

    # 最近 max_turns 轮全部保留
    recent = dialog_msgs[-(max_turns * 2):]

    # 早期历史中只保留与 query 有共同关键词的轮次
    early = dialog_msgs[:-(max_turns * 2)]
    if not early:
        return system_msgs + recent

    query_chars = set(query)
    kept_early = []
    for i in range(0, len(early), 2):
        if i + 1 >= len(early):
            break
        user_msg = early[i]
        assistant_msg = early[i + 1]
        # 如果用户问题和当前 query 有共同字符，保留这一轮
        user_chars = set(user_msg.get("content", ""))
        if user_chars & query_chars:
            kept_early.append(user_msg)
            kept_early.append(assistant_msg)

    return system_msgs + kept_early + recent
