import asyncio
import logging
import re
import traceback
from typing import AsyncGenerator

from langchain_core.messages import AIMessage, ToolMessage

from agent.deep_agent import deep_agent
from agent.routing import route as routing_route

logger = logging.getLogger(__name__)

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
        routing_result = routing_route(question, thread_id=thread_id)      #这里使用了route函数的别名routing_route
        intent = routing_result["intent"]      #routing_route函数返回一个字典,用字典的键值匹配来取值
        confidence = routing_result["confidence"]
        source = routing_result["source"]

        logger.info(
            f"意图路由: {intent} (conf={confidence:.2f}, source={source}) | "
            f"规则={routing_result['rule_detail']} | "
            f"BERT={routing_result['bert_detail']}"
        )

        # ========== 构造输入：意图注入 system message ==========
        system_message =[]

        intent_desc = {
            "NEO4J_QUERY": "企业内部知识图谱查询",
            "WEB_QUERY": "网络实时信息搜索",
            "CHITCHAT": "日常闲聊",
        }.get(intent, intent)   #表示要查找的键为intent 如果匹配上了就返回对应的值，如果没有匹配上就返回键名

        routing_system_message = (
            f"=*5外部意图分析结果=*5\n"
            f"意图: {intent}\n"
            f"意图描述: {intent_desc}\n"
            f"置信度: {confidence:.2f}\n"
            f"决策来源: {source}\n\n"
            f"请根据以上意图分类，将用户问题转发给对应的子Agent执行。"
        )

        system_message.append(routing_system_message)

        if not hasattr(deep_agent, 'astream'):
            return

        inputs = {
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": question},
            ]
        }
        config = {"configurable": {"thread_id": thread_id or "default_session"}}

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
                    async for piece in _yield_chunked(content, _cancelled):
                        yield piece

    except Exception as e:
        error_msg = f"处理问题时出错: {str(e)}"
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        yield error_msg