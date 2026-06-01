from agent.skills.web_search.scripts.web_search import internet_search
from utils.prompt_loader import load_prompt

web_search_subagent = {
    "name": "web-search-agent",
    "description":  """
    专门用于执行网络信息检索和查询的智能体
    适用场景
    - 需要从互联网获取最新信息、新闻、动
    - 需要验证事实、查找资料、文献检
    - 用户问题涉及实时数据、市场行情、技术文
    - 本地知识库无法回答的时效性问
    """,
    "tools": [internet_search],
    "system_prompt": load_prompt("web_search"),
    "skills": ["./skills/web_search"],  # 使用网络查询skill
}