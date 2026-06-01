# ========== 定义意图识别agent ==========
from utils.prompt_loader import load_prompt

intent_recognition_subagent = {
    "name": "intent-analyzer",
    "description": """
    你是一个专门用于分析用户输入意图的智能体
    适用场景：
    - 需要识别用户的问题是查询类、操作类、创作类还是闲聊?
    - 需要提取用户问题中的关键实体和参数
    - 需要判断任务的复杂度和所需工具
    - 需要为后续处理进行意图分类和路由决
    如果识别到意图是需要网络信息检索，那么将信息发给以下agent："web_search_subagent"
    """,
    "system_prompt": load_prompt("intent_recognition"),
    # 可选：为子 agent 指定更轻量的模型
    # "model": "gpt-3.5-turbo",  # 如果?agent 用的是复杂模型，这里可以用更快的模型
    # 可选：为子 agent 配备专用工具
    # "tools": [intent_classification_tool],  # 如果有一些预定义分类逻辑
}