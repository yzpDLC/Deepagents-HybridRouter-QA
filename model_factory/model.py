import logging
from abc import ABC, abstractmethod
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.embeddings import Embeddings
from langchain_community.chat_models.tongyi import BaseChatModel, ChatTongyi

from config.settings import settings

logger=logging.getLogger(__name__)

class BaseModelFactory(ABC):
    @abstractmethod
    def generator(self) -> Optional[Embeddings | BaseChatModel] :
        pass


class ChatModelFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        model_name = settings.chat_model_name.lower()

        if "qwen" in model_name:
            return ChatOpenAI(
                model=settings.chat_model_name,
                api_key=settings.dashscope_api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                temperature=settings.chat_model_temperature,
            )
        elif "deepseek" in model_name:
            return ChatOpenAI(
                model=settings.chat_model_name,
                api_key=settings.deepseek_api_key,
                base_url="https://api.deepseek.com/v1",
                temperature=settings.chat_model_temperature,
                model_kwargs={
                    "extra_body": {
                        "thinking": {"type": "disabled"}
                    }
                }
            )
        else:
            raise ValueError(f"使用了不支持的模型：{model_name}")

class EmbeddingFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | BaseChatModel] :
        return DashScopeEmbeddings(model=settings.embedding_model_name)


chat_model=ChatModelFactory().generator()
embed_model=EmbeddingFactory().generator()
