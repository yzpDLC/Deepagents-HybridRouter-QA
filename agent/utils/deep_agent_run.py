import asyncio
import logging
import re
import traceback
from typing import AsyncGenerator

from langchain_core.messages import AIMessage, ToolMessage

from agent.deep_agent import deep_agent
from agent.routing import route as routing_route
from agent.context import build_messages
from agent.context.build_memory import save_turn

logger = logging.getLogger()

_CHUNK_SIZE = 3  # 每次流式输出的字符数
_CHUNK_DELAY = 0.02  # 块之间的延迟（秒）


def _extract_message_content(msg):
    if hasattr(msg, 'content'):
        return msg.content
    if isinstance(msg, dict):
        return msg.get('content', '')
    return ""


def _should_yield(msg, has_yielded_tool: bool) -> tuple[bool, bool]:
    """返回 (should_yield, new_has_yielded_tool)"""
    if isinstance(msg, ToolMessage):
        return True, True
    if isinstance(msg, AIMessage):
        return (False, False) if has_yielded_tool else (True, False)
    if isinstance(msg, dict) and msg.get('role') == 'assistant':
        return True, has_yielded_tool
    return False, has_yielded_tool


async def _yield_chunked(content: str, cancel_check):
    """将内容按语义边界分块输出，模拟打字效果"""
    # 按中文字符 + 英文单词 + 标点分段
    tokens = re.findall(r'[一-鿿]|[\w]+|[^\w\s]|\s', content)
    buf = ''
    for token in tokens:
        if cancel_check():
            yield '\n\n[已停止生成]'
            return
        buf += token
        if len(buf) >= _CHUNK_SIZE:
            yield buf
            buf = ''
            await asyncio.sleep(_CHUNK_DELAY)
    if buf:
        yield buf


async def run_agent_streaming(question: str, cancel_event: asyncio.Event = None, thread_id: str = None) -> AsyncGenerator[str, None]:
    """流式运行 Agent（含外部意图路由层）"""
    if not deep_agent:
        yield "错误: Agent 未正确初始化，请检查配置"
        return

    def _cancelled():
        return cancel_event and cancel_event.is_set()

    try:
        logger.info(f"开始处理问题: {question[:50]}...")

        # ========== 外部路由层：两路并行 + 仲裁 ==========
        routing_result = routing_route(question, thread_id=thread_id)
        intent = routing_result["intent"]
        confidence = routing_result["confidence"]
        source = routing_result["source"]

        logger.info(
            f"意图路由: {intent} (conf={confidence:.2f}, source={source}) | "
            f"规则={routing_result['rule_detail']} | "
            f"BERT={routing_result['bert_detail']}"
        )

        # ========== 通过上下文模块组装 inputs ==========
        if not hasattr(deep_agent, 'astream'):
            return

        inputs = build_messages(
            intent=intent,
            confidence=confidence,
            question=question,
            thread_id=thread_id,
        )
        config = {"configurable": {"thread_id": thread_id or "default_session"}}

        # 收集完整的 AI 回复，用于保存历史
        full_assistant_response = ""

        async for chunk in deep_agent.astream(inputs, config=config, stream_mode="values"):
            if _cancelled():
                yield "\n\n[已停止生成]"
                return

            messages = chunk.get("messages")
            if not messages:
                continue

            last_message = messages[-1]

            # 工具日志
            if isinstance(last_message, AIMessage) and getattr(last_message, 'tool_calls', None):
                for tool_call in last_message.tool_calls:
                    logger.info(f"Skill 调用: {tool_call.get('name', 'unknown')}, 参数: {tool_call.get('args', {})}")
            elif isinstance(last_message, ToolMessage):
                logger.info(
                    f"Skill 结果: {getattr(last_message, 'name', 'unknown')}, 返回值: {str(last_message.content)[:200]}...")

            if isinstance(last_message, AIMessage):
                content = _extract_message_content(last_message)
                if content and isinstance(content, str):
                    full_assistant_response = content  # 暂存完整回复
                    async for piece in _yield_chunked(content, _cancelled):
                        yield piece

        # ========== 保存本轮对话到历史缓存 ==========
        if thread_id and full_assistant_response:
            save_turn(thread_id, question, full_assistant_response)

    except Exception as e:
        error_msg = f"处理问题时出错: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        yield error_msg