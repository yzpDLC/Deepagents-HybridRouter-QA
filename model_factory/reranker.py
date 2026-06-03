"""
重排序模型工厂
统一管理 Cross-Encoder 重排模型的加载和选择
模型信息从配置中心（config/settings.py）的注册表读取，新增模型无需改代码

企业规范要点：
- 单例模式：模型只加载一次，后续调用复用缓存
- 配置驱动：所有参数从 settings 读取，不硬编码
- 注册表扩展：新增模型只需在 settings 的 reranker_model_registry 中添加记录
"""
import logging
import os
from pathlib import Path

from sentence_transformers import CrossEncoder
import torch

from config.settings import settings

logger = logging.getLogger(__name__)

# 模型实例缓存（单例模式），key=模型名，value=模型实例
_instances: dict[str, CrossEncoder] = {}


def _resolve_model_path(model_name: str) -> str:
    """解析模型路径：支持相对路径（项目根目录）和绝对路径"""
    registry = settings.reranker_model_registry
    if model_name not in registry:
        raise KeyError(
            f"未知的重排模型: '{model_name}'。"
            f"可用模型: {list(registry.keys())}。"
            f"请在 config/settings.py 的 reranker_model_registry 中添加该模型配置。"
        )

    model_path = registry[model_name]["path"]
    if not os.path.isabs(model_path):
        model_path = str(Path(__file__).resolve().parent.parent / model_path)
    return model_path


def get_reranker(model_name: str | None = None) -> CrossEncoder:
    """
    获取重排序模型实例（单例，只加载一次）

    Args:
        model_name: 模型名称，必须是 reranker_model_registry 中的 key。
                    默认从 settings.reranker_model_name 读取。

    Returns:
        CrossEncoder 模型实例
    """
    if model_name is None:
        model_name = settings.reranker_model_name

    if model_name not in _instances:
        # 确定计算设备
        device = "cuda" if torch.cuda.is_available() else "cpu"

        # 从注册表读取配置
        registry = settings.reranker_model_registry
        if model_name not in registry:
            raise KeyError(
                f"未知的重排模型: '{model_name}'。"
                f"可用模型: {list(registry.keys())}。"
            )

        model_config = registry[model_name]
        model_path = _resolve_model_path(model_name)
        max_length = model_config.get("max_length", settings.reranker_max_length)

        logger.info(
            f"加载重排模型: {model_name} "
            f"(path={model_path}, device={device}, max_length={max_length})"
        )

        _instances[model_name] = CrossEncoder(
            model_path,
            max_length=max_length,
            device=device,
        )

        logger.info("重排模型加载完成")
    return _instances[model_name]


def rerank(
    query: str,
    documents: list[str],
    top_k: int = 5,
    model_name: str | None = None,
) -> list[tuple[str, float]]:
    """
    对检索结果进行语义重排序

    Args:
        query: 用户查询问题
        documents: 候选文档列表
        top_k: 保留前几个结果，默认 5
        model_name: 指定使用的重排模型，必须是 reranker_model_registry 中的 key。
                    默认从 settings.reranker_model_name 读取。

    Returns:
        list[tuple[str, float]]: 按相关性分数降序排列的 (文档, 分数) 列表

    Raises:
        KeyError: 当指定的 model_name 不在注册表中时抛出
    """
    if not documents:
        return []

    model = get_reranker(model_name)

    # 将 query 与每篇文档组成一对，由模型评估相关性
    pairs = [[query, doc] for doc in documents]
    scores = model.predict(pairs)

    # 按分数从高到低排序
    ranked = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)

    logger.info(f"重排序完成: 输入 {len(documents)} 条，保留 top-{top_k}")
    return ranked[:top_k]
