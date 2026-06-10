"""上下文拼装模块

提供三层记忆体系的 messages 构建能力：
1. 系统指令层（路由意图、安全限制）
2. 工作记忆层（最近 N 轮对话历史）
3. 用户输入层（当前问题）

用法:
    from agent.context import build_messages

    inputs = build_messages(
        intent="KNOWLEDGE_QUERY",
        confidence=0.92,
        question="请假流程是什么",
        thread_id="session_001",
    )
    # inputs = {"messages": [...]}
    async for chunk in deep_agent.astream(inputs, config=config, stream_mode="values"):
"""

from .build_context import build_messages

__all__ = ["build_messages"]
