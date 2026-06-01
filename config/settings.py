"""
统一配置中心
所有配置字段集中定义，带类型校验，支持环境变量 / .env 文件 / 默认值三层覆盖
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ========== LLM ==========
    chat_model_name: str = "deepseek-v4-pro"
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


settings = Settings()

# Prompt 文件路径映射（prompt_loader中加载提示词是通过字典的键值匹配来获取对应的文件路径）
prompts_conf = {
    "main_agent": "prompts/main_agent.txt",
    "intent_recognition": "prompts/intent_recognition.txt",
    "web_search": "prompts/web_search.txt",
    "neo4j_query": "prompts/neo4j_query.txt",
    "text_to_video": "prompts/text_to_video.txt",
}
