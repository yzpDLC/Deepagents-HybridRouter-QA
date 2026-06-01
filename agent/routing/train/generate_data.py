"""
训练数据生成脚本
用当前 LLM 对地震文档生成 query 并标注意图
在终端中运行: python -m agent.routing.train.generate_data

输出: agent/routing/train/training_data.jsonl
"""

import json
import logging
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from utils.path_tool import get_abs_path
from utils.prompt_loader import load_prompt
from model_factory.model import chat_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 输出路径
OUTPUT_PATH = Path(__file__).resolve().parent / "training_data.jsonl"

# 意图标签
INTENTS = ["NEO4J_QUERY", "WEB_QUERY", "CREATE"]

# 用于生成地震 query 的源文档（从 graphrag/input/ 获取）
INPUT_DIR = Path(get_abs_path("graphrag/input"))

# 各意图的生成模板
GENERATION_TEMPLATES = {
    "NEO4J_QUERY": (
        "你是一个地震知识问答系统的用户。请根据以下地震相关文档内容，"
        "生成 {num} 个用户可能会问的自然问题。问题应该覆盖：概念查询、方法咨询、"
        "数据查询、原因解释等类型。只输出问题，每行一个，不要编号。\n\n文档内容:\n{document}"
    ),
    "WEB_QUERY": (
        "你是一个地震知识问答系统的用户。请生成 {num} 个需要联网实时搜索才能回答的问题。"
        "涉及：最新地震动态、当前新闻、实时数据、时间敏感信息等。"
        "只输出问题，每行一个，不要编号。"
    ),
    "CREATE": (
        "你是一个地震知识问答系统的用户。请生成 {num} 个要求创建或编写新技能的请求。"
        "例如：创建分析工具、生成脚本、开发新功能等。"
        "只输出问题，每行一个，不要编号。"
    ),
}


def load_source_documents() -> list[str]:
    """从 graphrag/input/ 加载源文档"""
    documents = []
    if INPUT_DIR.exists():
        for file_path in INPUT_DIR.glob("*"):
            if file_path.suffix in [".txt", ".md", ".pdf"]:
                try:
                    if file_path.suffix == ".pdf":
                        continue  # PDF 解析较复杂，跳过
                    text = file_path.read_text(encoding="utf-8", errors="ignore")
                    # 按段落拆分
                    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 50]
                    documents.extend(paragraphs[:20])
                except Exception as e:
                    logger.warning(f"读取文件 {file_path} 失败: {e}")
    if not documents:
        # 保底文档
        documents = [
            "地震是地壳快速释放能量造成的振动，由板块运动引起。主要分为构造地震、火山地震和陷落地震。",
            "地震预警系统通过监测纵波（P波）和横波（S波）的时间差，在破坏性横波到达前发出警报。",
            "地震应急演练内容包括：紧急避险、有序疏散、伤员救护、物资调配、通信联络等环节。",
            "地震发生时，应迅速躲到坚固的桌下或墙角，保护头部，远离窗户和高大家具。",
            "震级衡量地震释放的能量大小，烈度衡量地表受破坏程度。一次地震只有一个震级，但有多个烈度。",
        ]
    return documents


def generate_queries_for_intent(
    intent: str,
    num_per_doc: int = 5,
) -> list[str]:
    """用 LLM 为指定意图生成 query"""
    queries = []

    if intent == "WEB_QUERY":
        # WEB_QUERY 不依赖文档
        prompt = GENERATION_TEMPLATES["WEB_QUERY"].format(num=num_per_doc)
        try:
            response = chat_model.invoke(prompt)
            lines = response.content.strip().split("\n")
            queries = [line.strip("- •0123456789.、 ").strip() for line in lines if line.strip()]
        except Exception as e:
            logger.error(f"WEB_QUERY 生成失败: {e}")
        queries = queries[:num_per_doc]
        # 如果 LLM 失败，用模板填充
        if not queries:
            queries = [
                "最近有地震发生吗",
                "今天的地震新闻",
                "搜索最新的地震动态",
                "查一下当前的天气情况",
                "最近一周有什么自然灾害报道",
            ]
        return queries

    if intent == "CREATE":
        prompt = GENERATION_TEMPLATES["CREATE"].format(num=num_per_doc)
        try:
            response = chat_model.invoke(prompt)
            lines = response.content.strip().split("\n")
            queries = [line.strip("- •0123456789.、 ").strip() for line in lines if line.strip()]
        except Exception as e:
            logger.error(f"CREATE 生成失败: {e}")
        if not queries:
            queries = [
                "帮我创建一个地震数据查询工具",
                "生成一个自动分析地震报告的技能",
                "帮我写一个地震应急指南生成脚本",
                "开发一个地震知识问答插件",
                "帮我创建一个地震演练评估工具",
            ]
        return queries

    # NEO4J_QUERY：基于文档生成
    documents = load_source_documents()
    for doc in documents[:5]:  # 最多用前5段
        prompt = GENERATION_TEMPLATES["NEO4J_QUERY"].format(num=num_per_doc, document=doc)
        try:
            response = chat_model.invoke(prompt)
            lines = response.content.strip().split("\n")
            doc_queries = [line.strip("- •0123456789.、 ").strip() for line in lines if line.strip()]
            queries.extend(doc_queries[:num_per_doc])
        except Exception as e:
            logger.error(f"NEO4J_QUERY 生成失败: {e}")

    # 保底
    if not queries:
        queries = [
            "地震时应该怎么做",
            "什么是地震预警系统",
            "汶川地震的基本信息",
            "地震应急演练有哪些内容",
            "地震的成因是什么",
            "震级和烈度有什么区别",
            "地震时在室内如何避险",
            "学校应该如何进行地震演练",
            "地震预警系统的工作原理",
            "地震应急物资有哪些",
        ]
    return queries


def main():
    """主流程：生成标注数据"""
    logger.info("开始生成训练数据...")
    logger.info(f"输出路径: {OUTPUT_PATH}")

    total = 0
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for intent in INTENTS:
            logger.info(f"正在生成 intent={intent} 的数据...")
            queries = generate_queries_for_intent(intent, num_per_doc=5)

            for query in queries:
                if not query:
                    continue
                record = {
                    "query": query,
                    "intent": intent,
                    "history_context": "",  # 单轮数据，后续可扩展
                    "source": "llm_generated",
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                total += 1

    logger.info(f"生成完成！共 {total} 条数据")
    logger.info(f"建议: 人工检查 {OUTPUT_PATH} 并修正明显错误后再训练")


if __name__ == "__main__":
    main()
