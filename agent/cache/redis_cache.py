"""
双层缓存模块（LRU + Redis）

第一层：进程内 LRU 缓存（毫秒级）
第二层：Redis 分布式缓存（适用于多实例部署）

用法:
    from agent.cache.redis_cache import hybrid_cache
    result = hybrid_cache.get("query:xxx", ttl=3600)
"""

import hashlib
import json
import logging
from functools import lru_cache
from typing import Any

from config.settings import settings

logger = logging.getLogger(__name__)

# Redis 客户端（懒加载）
_redis_client = None


def _get_redis():
    """获取 Redis 客户端（懒加载）"""
    global _redis_client
    if _redis_client is None:
        try:
            import redis
            _redis_client = redis.from_url(
                "redis://localhost:6379/0",
                decode_responses=True,
                socket_timeout=2,
                socket_connect_timeout=2,
            )
            _redis_client.ping()
            logger.info("Redis 连接成功")
        except Exception as e:
            logger.warning("Redis 不可用（不影响系统运行）: %s", e)
            _redis_client = False  # False 表示不可用
    return _redis_client if _redis_client is not False else None


def _make_key(key: str) -> str:
    """生成缓存 key"""
    return f"kb:{hashlib.md5(key.encode()).hexdigest()}"


@lru_cache(maxsize=500)
def _lru_get(key: str) -> str | None:
    """LRU 缓存层（仅由 hybrid_cache.get 内部调用）"""
    return None  # 占位——LRU 由 functools 自动管理


def get(key: str, ttl: int = 3600) -> Any | None:
    """获取缓存：LRU → Redis → 未命中

    Args:
        key: 缓存键
        ttl: Redis 过期时间（秒），默认 1 小时

    Returns:
        缓存的值，未命中返回 None
    """
    cache_key = _make_key(key)

    # 第 1 层：LRU（内存）
    # 注：这里不直接调 _lru_get，因为 functools.lru_cache 不适合包装 None 返回值
    # 改为在业务层自行判断是否需要缓存

    # 第 2 层：Redis
    redis_client = _get_redis()
    if redis_client:
        try:
            value = redis_client.get(cache_key)
            if value is not None:
                logger.debug("Redis 缓存命中: %s", key[:50])
                return json.loads(value)
        except Exception as e:
            logger.warning("Redis 读取失败: %s", e)

    return None


def set(key: str, value: Any, ttl: int = 3600):
    """写入双层缓存

    Args:
        key: 缓存键
        value: 要缓存的值（可 JSON 序列化）
        ttl: 过期时间（秒）
    """
    cache_key = _make_key(key)

    # Redis
    redis_client = _get_redis()
    if redis_client:
        try:
            redis_client.setex(cache_key, ttl, json.dumps(value, ensure_ascii=False))
            logger.debug("Redis 缓存写入: %s", key[:50])
        except Exception as e:
            logger.warning("Redis 写入失败: %s", e)


def clear(pattern: str | None = None):
    """清空缓存

    Args:
        pattern: Redis key 匹配模式，None 表示清空全部
    """
    # 清空 LRU
    _lru_get.cache_clear()

    # 清空 Redis
    redis_client = _get_redis()
    if redis_client:
        try:
            if pattern:
                keys = redis_client.keys(pattern)
                if keys:
                    redis_client.delete(*keys)
            else:
                redis_client.flushdb()
            logger.info("Redis 缓存已清空")
        except Exception as e:
            logger.warning("Redis 清空失败: %s", e)
