"""
文字生成视频工具脚本
使用火山方舟 Seedance API 生成视频
"""

import time
from typing import Any, Optional

import requests
from langchain_core.tools import tool

from config.settings import settings


# API 配置
_API_KEY = settings.huoshan_api_key
_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
_TASKS_URL = f"{_BASE_URL}/contents/generations/tasks"
_MODEL = "doubao-seedance-1-5-pro-251215"
_POLL_INTERVAL = 5
_POLL_TIMEOUT = 300


@tool
def text_to_video(
    prompt: str,
    duration: int = 5,
    resolution: str = "720p",
    ratio: str = "16:9",
    seed: Optional[int] = None,
) -> dict[str, Any]:
    """
    一个使用火山方舟 Seedance API 生成视频的文本生成视频工具

    Args:
        prompt: 视频生成提示词
        duration: 视频时长（秒），默认5
        resolution: 视频分辨率，默认720p
        ratio: 视频画面比例，默认16:9
        seed: 随机种子，可选

    Returns:
        dict: 包含视频生成结果的字典
    """
    # 检查 API Key
    if not _API_KEY:
        raise ValueError("请设置环境变量 ARK_API_KEY")

    # 构建请求参数
    payload = {
        "model": _MODEL,
        "content": [{"type": "text", "text": prompt}],
        "duration": duration,
        "resolution": resolution,
        "ratio": ratio,
        "watermark": False,
    }
    if seed is not None:
        payload["seed"] = seed

    try:
        start_time = time.time()

        # 提交生成任务
        headers = {
            "Authorization": f"Bearer {_API_KEY}",
            "Content-Type": "application/json",
        }
        resp = requests.post(_TASKS_URL, headers=headers, json=payload, timeout=60)
        data = resp.json()

        if resp.status_code != 200:
            error_msg = data.get("error", {}).get("message", str(data))
            return {
                "error": error_msg,
                "prompt": prompt,
                "success": False
            }

        task_id = data["id"]
        # 轮询任务结果
        deadline = time.time() + _POLL_TIMEOUT
        while time.time() < deadline:
            resp = requests.get(f"{_TASKS_URL}/{task_id}", headers=headers, timeout=30)
            data = resp.json()
            status = data.get("status")

            if status == "succeeded":
                return {
                    "success": True,
                    "prompt": prompt,
                    "duration": duration,
                    "resolution": resolution,
                    "video_url": data.get("content", {}).get("video_url", ""),
                    "elapsed_seconds": round(time.time() - start_time, 1)
                }

            if status in ["failed", "expired", "cancelled"]:
                return {
                    "success": False,
                    "prompt": prompt,
                    "error": data.get("error", {}).get("message", status)
                }

            time.sleep(_POLL_INTERVAL)

        # 超时返回
        return {
            "success": False,
            "prompt": prompt,
            "error": f"任务超时（{_POLL_TIMEOUT}s）"
        }

    except Exception as e:
        return {
            "error": str(e),
            "prompt": prompt,
            "success": False
        }


if __name__ == "__main__":
    # 测试示例
    import json

    print("=== 文本生成视频测试 ===")
    result = text_to_video("海边日落，唯美风景", duration=5)  #duration=5 默认为5秒
    print(json.dumps(result, ensure_ascii=False, indent=2))