from agent.skills.neo4j_query.scripts.neo4j_query import graphrag_earthquake_search
from utils.prompt_loader import load_prompt

neo4j_subagent = {
    "name": "neo4j-query-agent",
    "description": """
    专门用于执行Neo4j图数据库查询和分析的智能体
    适用场景
    - 需要查询实体关系、知识图谱信
    - 需要进行图数据分析、路径查找、节点关联分
    - 用户问题涉及数据之间的关联关系、依赖关
    - 需要从图数据库中检索结构化知识
    - 实体关系推理、社交网络分析、推荐系统查
    """,
    "tools": [graphrag_earthquake_search],
    "system_prompt": load_prompt("neo4j_query"),
}
