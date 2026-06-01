---
name: text_to_video
description: 使用火山方舟 Seedance API 将文字生成视频。每次调用同步阻塞 30-120 秒，内部自动轮询。
---

# text_to_video

通过 `execute` 工具运行脚本生成视频。脚本已内置异步提交 + 轮询，调用即阻塞等待直到完成或超时。

## 执行命令

```bash
python skills/text_to_video/scripts/text_to_video.py "视频描述文本" --duration 5 --resolution 720p
```

完整参数示例：
```bash
python skills/text_to_video/scripts/text_to_video.py "视频描述文本" --duration 8 --resolution 1080p --ratio 9:16 --seed 42
```

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `视频描述` | 中文视频描述文本，100-300 字为佳 | 必填 |
| `--duration` | 视频时长（秒），建议 5 | 5 |
| `--resolution` | 480p / 720p / 1080p | 720p |
| `--ratio` | 16:9 / 9:16 / 1:1 | 16:9 |
| `--seed` | 固定种子可复现结果 | 随机 |

## 返回格式

成功：
```json
{
  "success": true,
  "task_id": "cgt-xxx",
  "status": "succeeded",
  "video_url": "https://...",
  "elapsed_seconds": 56.6
}
```

失败：
```json
{
  "success": false,
  "error": "错误描述"
}
```

## 注意事项
- 每次调用耗时 30-120 秒，300 秒超时
- 视频 URL 有效期 24 小时
- 分辨率越高耗时越长，无特别要求时使用 720p
- 禁止生成违法违规内容
