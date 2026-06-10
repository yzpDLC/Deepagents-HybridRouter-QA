"""上下文拼装——统筹系统指令、工作记忆与用户输入，组装最终 inputs"""

from .build_system import build_system_message
from .build_memory import build_working_memory, semantic_prune

# 意图中文描述映射
_INTENT_DESC = {
    "NEO4J_QUERY": "企业内部知识图谱查询",
    "WEB_QUERY": "网络实时信息搜索",
    "CHITCHAT": "日常闲聊",
}

# 模型上下文窗口上限（qwen3.5-flash 约 32K，留 2K 缓冲）
_MAX_CONTEXT_TOKENS = 30000

# 系统指令的预估 token 数（固定值，避免重复估算）
_SYSTEM_TOKEN_ESTIMATE = 150


def _estimate_tokens(text: str) -> int:
    """粗略估算 token 数：中文约 2 字/token，英文约 1 词/token"""
    text = text.strip()
    if not text:
        return 0
    # 简单估算：字符数 / 2
    return max(1, len(text) // 2)


def _truncate_by_token_limit(messages: list[dict], max_tokens: int = _MAX_CONTEXT_TOKENS) -> list[dict]:
    """Token 截断保护——总 token 超限时从最早的非 system 消息开始丢弃

    这是最后一道防线，在滑动窗口和语义裁剪之后执行。
    """
    system_msgs = [m for m in messages if m["role"] == "system"]
    dialog_msgs = [m for m in messages if m["role"] != "system"]

    # 计算 system 已占用的 token
    system_tokens = sum(_estimate_tokens(m["content"]) for m in system_msgs)

    # 剩余预算给对话消息
    budget = max_tokens - system_tokens - 500  # 留 500 缓冲

    result_dialog = []
    # 从最新的消息开始保留（最相关）
    for m in reversed(dialog_msgs):
        msg_tokens = _estimate_tokens(m["content"])
        if msg_tokens <= budget:
            result_dialog.insert(0, m)
            budget -= msg_tokens
        else:
            break

    return system_msgs + result_dialog


def build_messages(
    intent: str,
    confidence: float,
    question: str,
    thread_id: str | None = None,
) -> dict:
    """组装上下文，返回 astream 可直接使用的 inputs 字典

    处理流程：
    1. 构建系统指令
    2. 滑动窗口读取历史
    3. 语义裁剪（剔除不相关历史）
    4. Token 截断保护（最后防线）

    Args:
        intent: 意图名称
        confidence: 置信度
        question: 用户当前输入
        thread_id: 会话标识

    Returns:
        dict: {"messages": [...]} 格式
    """
    intent_desc = _INTENT_DESC.get(intent, intent)

    # ========== 步骤 1：系统指令 ==========
    system_message = build_system_message(intent, intent_desc, confidence)

    # ========== 步骤 2：滑动窗口读取历史 ==========
    working_memory = build_working_memory(thread_id)

    # ========== 步骤 3：初步组装 messages ==========
    messages = []
    for msg in system_message:
        messages.append({"role": "system", "content": msg})
    messages.extend(working_memory)
    messages.append({"role": "user", "content": question})

    print(f"messages:{messages}")  #---------------------------------打印出来传的上下文具体是什么
    # ========== 步骤 4：语义裁剪 ==========
    messages = semantic_prune(messages, question)

    # ========== 步骤 5：Token 截断保护 ==========
    messages = _truncate_by_token_limit(messages)

    return {"messages": messages}
