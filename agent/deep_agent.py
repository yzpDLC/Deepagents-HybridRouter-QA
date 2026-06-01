
from pathlib import Path
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langgraph.checkpoint.memory import MemorySaver

from agent.subagent.neo4j_subagent import neo4j_subagent
from agent.subagent.text_to_video_subagent import text_to_video_subagent
from agent.subagent.web_search_subagent import web_search_subagent
from utils.prompt_loader import load_prompt
from model_factory.model import chat_model

project_root = Path(__file__).parent.resolve()

backend = FilesystemBackend(
    root_dir=str(project_root),
    virtual_mode=True
)

subagents = [web_search_subagent, neo4j_subagent, text_to_video_subagent]

checkpointer = MemorySaver()

# 创建 DeepAgent
# 意图路由已由外部 agent/routing/ 模块独立完成（规则引擎 + BERT + 仲裁）
# Agent 的 system_prompt 不再包含路由规则，路由信息通过 system message 注入
deep_agent = None
if chat_model:
    try:
        deep_agent = create_deep_agent(
            model=chat_model,
            skills=["./skills/skill-creator"],
            backend=backend,
            system_prompt=load_prompt("intent_recognition"),
            subagents=subagents,
            checkpointer=checkpointer,
        )
        print("Deep Agent 初始化成功，外部路由层就绪")
    except Exception as e:
        print(f"Deep Agent 初始化失败: {e}")
else:
    print("警告: 模型未配置，Agent 将不可用")
