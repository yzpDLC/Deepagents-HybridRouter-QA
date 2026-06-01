"""
联网搜索工具脚本
使用 Tavily API 进行网络搜索
"""

from typing import Literal

from langchain_core.tools import tool
from tavily import TavilyClient

from config.settings import settings


@tool
def internet_search(
        query: str,
        max_results: int = 5,
        topic: Literal["general", "news", "finance"] = "general",
        include_raw_content: bool = False,
):
    """
    一个使用 Tavily API 进行网络搜索的互联网搜索工具

    Args:
        query: 搜索查询字符串
        max_results: 返回结果数量，默认5，建议范围3-10
        topic: 搜索主题，支持 "general"(通用), "news"(新闻), "finance"(金融)
        include_raw_content: 是否返回原始网页内容，默认False

    Returns:
        dict: 包含搜索结果的字典
            {
                "results": [
                    {
                        "title": str,
                        "url": str,
                        "content": str,
                        "score": float
                    }
                ],
                "query": str,
                "response_time": float
            }
    """
    if not settings.tavily_api_key:
        raise ValueError("请设置 TAVILY_API_KEY（.env 或环境变量）")
    tavily_client = TavilyClient(api_key=settings.tavily_api_key)

    # 执行搜索
    try:
        response = tavily_client.search(
            query=query,
            max_results=max_results,
            include_raw_content=include_raw_content,
            topic=topic,
        )
        return response
    except Exception as e:
        return {
            "error": str(e),
            "query": query,
            "results": []
        }




if __name__ == "__main__":
    # 测试示例
    import json

    # 示例1：通用搜索
    print("=== 通用搜索测试 ===")
    result = internet_search("现在是2026年，崩坏星穹铁道有什么活动？", max_results=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # # 示例2：新闻搜索
    # print("\n=== 新闻搜索测试 ===")
    # news = news_search("人工智能最新进展", max_results=2)
    # print(json.dumps(news, ensure_ascii=False, indent=2))