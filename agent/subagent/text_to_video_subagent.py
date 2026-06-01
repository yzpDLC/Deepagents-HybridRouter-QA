from utils.prompt_loader import load_prompt
from agent.skills.text_to_video.scripts.text_to_video import text_to_video


text_to_video_subagent = {
    "name": "text_to_video-agent",
    "description": """
    专门用于将文字描述生成视频的智能体。
    适用场景：
    - 用户要求生成视频、制作动画、可视化场景
    - 从对话历史中提取地震知识要点并逐段生成视频
    - 将文本描述转化为视频素材
    """,
    "tools": [text_to_video],
    "system_prompt": load_prompt("text_to_video"),
    "skills": ["./skills/text_to_video"],
}