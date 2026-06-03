import asyncio
import json
import sys
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from agent.deep_agent import deep_agent
from agent.utils.deep_agent_run import run_agent_streaming

"""
企业内部多源知识库问答系统
启动方式：命令行输入uvicorn web.app:app
"""
app = FastAPI(title="企业内部多源知识库问答系统")

_cancel_events: dict[str, asyncio.Event] = {}

_base_dir = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(_base_dir / "static")), name="static")

_index_html = (_base_dir / "templates" / "index.html").read_text(encoding="utf-8")


@app.get("/")
async def index():
    return HTMLResponse(content=_index_html)


@app.post("/api/chat/stream")
async def chat_stream(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="请求体格式错误")

    query = body.get("message", "").strip()
    session_id = body.get("session_id", "")

    if not query:
        raise HTTPException(status_code=400, detail="请输入问题")

    cancel_event = asyncio.Event()
    if session_id:
        _cancel_events[session_id] = cancel_event

    async def event_generator():
        try:
            async for chunk in run_agent_streaming(query, cancel_event, thread_id=session_id):
                if chunk:
                    yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
        finally:
            if session_id:
                _cancel_events.pop(session_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.post("/api/chat/cancel")
async def chat_cancel(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    session_id = body.get("session_id", "")
    if session_id and session_id in _cancel_events:
        _cancel_events[session_id].set()
        return {"status": "cancelled"}
    return {"status": "no_active_session"}


@app.get("/api/health")
async def health():
    agent_ok = deep_agent is not None
    model_ok = False
    try:
        from model_factory.model import chat_model
        model_ok = chat_model is not None
    except Exception:
        pass
    return {
        "status": "healthy",
        "agent_loaded": agent_ok,
        "model_loaded": model_ok,
    }


@app.post("/api/chat/generate-video")
async def generate_video(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="请求体格式错误")

    messages = body.get("messages", [])
    session_id = body.get("session_id", "")

    if not messages:
        raise HTTPException(status_code=400, detail="对话历史为空")

    history_lines = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            history_lines.append(f"用户：{content}")
        elif role == "assistant":
            history_lines.append(f"AI：{content}")

    history_text = "\n".join(history_lines)

    query = (
        '【视频生成任务】用户点击了"生成视频"按钮，需要你将以下对话历史中的知识要点转化为视频。'
        "你的工作：1）提取知识要点；2）为每个要点写一段100-300字的视频描述；"
        "3）调用text_to_video skill依次生成视频。\n\n"
        f"对话历史：\n{history_text}"
    )

    cancel_event = asyncio.Event()
    if session_id:
        _cancel_events[session_id] = cancel_event

    async def event_generator():
        try:
            async for chunk in run_agent_streaming(query, cancel_event, thread_id=session_id):
                if chunk:
                    yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
        finally:
            if session_id:
                _cancel_events.pop(session_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web.app:app", host="127.0.0.1", port=5000, reload=True)
