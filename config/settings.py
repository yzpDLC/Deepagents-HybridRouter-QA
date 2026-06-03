"""
统一配置中心
所有配置字段集中定义，带类型校验，支持环境变量 / .env 文件 / 默认值三层覆盖
环境变量 > .env > settings配置中心
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ========== LLM ==========
    chat_model_name: str = "deepseek-v4-flash"
    embedding_model_name: str = "text-embedding-v4"
    chat_model_temperature: float = 0.7
    deepseek_api_key: str = ""
    dashscope_api_key: str = ""

    # ========== Neo4j ==========
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "12345678"

    # ========== API Keys ==========
    tavily_api_key: str = ""
    huoshan_api_key: str = ""
    graphrag_api_key: str = ""

    # ========== BERT Routing ==========
    bert_model_path: str = "agent/routing/model"
    bert_max_length: int = 128

    # ========== Reranker ==========
    reranker_model_name: str = "bge-reranker-v2-m3"
    reranker_model_path: str = "models/bge-reranker-v2-m3"
    reranker_max_length: int = 8192

    # 重排模型注册表：这里配置重拍模型的具体名称，最大长度，模型地址和模型描述
    # 新增模型只需在此添加一条记录
    reranker_model_registry: dict = {
        "bge-reranker-v2-m3": {
            "path": "models/bge-reranker-v2-m3",
            "max_length": 8192,
            "description": "通用中英文重排模型，精度优先",
        },
        # 未来可尝试扩展轻量级的重拍模型，我这个模型太大了：
        # "bge-reranker-v2-light": {
        #     "path": "models/bge-reranker-v2-light",
        #     "max_length": 512,
        #     "description": "轻量重排模型，速度优先",
        # },
    }


settings = Settings()

# Prompt 文件路径映射（prompt_loader中加载提示词是通过字典的键值匹配来获取对应的文件路径）
prompts_conf = {
    "main_agent": "prompts/main_agent.txt",
    "intent_recognition": "prompts/intent_recognition.txt",
    "web_search": "prompts/web_search.txt",
    "neo4j_query": "prompts/neo4j_query.txt",
    "text_to_video": "prompts/text_to_video.txt",
}
