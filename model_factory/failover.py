"""
模型故障切换模块（懒探测模式）

参考 WeKnora 的懒探测设计：
- 不主动心跳探测，仅在调用失败时触发切换
- 瞬态错误（网络超时等）不缓存，下次自动重试
- 永久错误（API Key 无效等）缓存，后续直接走备用
"""

import logging
import time

from langchain_openai import ChatOpenAI

from config.settings import settings
from utils.logger_handler import get_logger

logger = get_logger()

# 主模型永久失败标记缓存  存储调用失败的模型名称集合
_permanent_failures: set[str] = set()

# 备用模型缓存（只创建一次）
_fallback_instance = None

# 最后一次切换时间（上一次容灾切换的时间）
_last_failover_time: float = 0.0


def _is_transient_error(exception: Exception) -> bool:
    """判断是否为瞬态错误——这类错误不缓存，下次可重试"""
    err_str = str(exception).lower()

    if ( tra_err in err_str for tra_err in settings.failover_transient_error):
        return True

    return False


def _create_fallback_model() -> ChatOpenAI:

    """创建备用模型（使用线上第二套 API Key 的模型 之后可以使用本地ollama部署的模型）"""
    global _fallback_instance
    if _fallback_instance is not None:
        logger.info(f"备用模型（{settings.failover_model}）已被启用\n\n")
        return _fallback_instance

    _fallback_instance=ChatOpenAI(
        model=settings.failover_model,
        api_key=settings.dashscope_api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        temperature=settings.failover_model_temperature,
    )
    logger.info(f"备用模型（{settings.failover_model}）已被启用\n\n")
    return _fallback_instance


def get_chat_model(model_name: str | None = None) -> ChatOpenAI | None:
    """获取 LLM 客户端，主模型失败时自动切换备用

    Args:
        model_name: 指定使用哪个主模型，默认从 settings 读取

    Returns:
        ChatOpenAI 实例
    """
    # 如果容灾开关是关闭状态 直接返回原始的模型工厂创建的模型
    if not settings.failover_enabled:
        from model_factory.model import ChatModelFactory
        return ChatModelFactory().generator()

    # 如果调用时没有指定模型，就从配置中心读取配置
    if model_name is None:
        model_name = settings.chat_model_name

    # 如果模型已被标记为永久失败，直接走备用
    if model_name in _permanent_failures:
        logger.warning(f"模型({model_name})已被标记为不可用，直接走备用")
        return _create_fallback_model()

    # 尝试主模型
    try:
        from model_factory.model import ChatModelFactory
        llm = ChatModelFactory().generator()
        # 创建后立即测试连通性（触发真实的 API 校验）
        logger.info(f"主模型({model_name})已创建，正在测试连通性...")
        llm.invoke("连通性测试")
        logger.info(f"主模型({model_name})连通性测试通过")
        return llm
    except Exception as e:
        # 声明全局变量，如果只是读取可以不用声明
        global _last_failover_time
        _last_failover_time = time.time()
        #是否是瞬态错误(暂时的，可以恢复)
        if _is_transient_error(e):
            logger.warning(f"模型 {model_name} 瞬态错误{str(e):.60}，切换至备用")
            return _create_fallback_model()
        else:
            logger.error(f"模型 {model_name} 永久错误 {str(e):.60}，标记为不可用")
            _permanent_failures.add(model_name)
            return _create_fallback_model()


def reset_failover():
    """手动重置容灾状态"""
    global _permanent_failures, _fallback_instance, _last_failover_time
    _permanent_failures.clear()
    _fallback_instance = None
    _last_failover_time = 0.0
    logger.info("容灾状态已重置")


def get_failover_status() -> dict:
    """获取当前容灾状态"""
    return {
        "primary_available": settings.chat_model_name not in _permanent_failures,
        "fallback_configured": settings.fallback_configured,
        "fallback_active": bool(_fallback_instance),
        "last_failover_time": _last_failover_time,
        "permanent_failures": list(_permanent_failures),
    }


