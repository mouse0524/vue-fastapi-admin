import json
import os
import uuid

from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import StreamingResponse

from app.controllers.ai_kb import ai_kb_controller
from app.controllers.system_setting import system_setting_controller
from app.core.ctx import CTX_USER_ID
from app.schemas.ai_kb import AIKbChatIn, AIKbConfigIn, AIKbFeedbackIn
from app.schemas.base import Fail, Success, SuccessExtra
from app.settings import settings

router = APIRouter()


@router.post("/chat", summary="AI知识库问答")
async def ai_kb_chat(payload: AIKbChatIn):
    data = await ai_kb_controller.chat(question=payload.question, top_k=payload.top_k)
    return Success(data=data)


@router.get("/chat/stream", summary="AI知识库流式问答")
async def ai_kb_chat_stream(
    question: str = Query(..., description="用户问题"),
    top_k: int = Query(5, ge=1, le=20, description="检索片段数量"),
):
    async def event_iter():
        async for event in ai_kb_controller.stream_chat(question=question, top_k=top_k):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_iter(), media_type="text/event-stream")


@router.post("/feedback", summary="AI知识库反馈")
async def ai_kb_feedback(payload: AIKbFeedbackIn):
    user_id = CTX_USER_ID.get()
    result = await ai_kb_controller.save_feedback(user_id=user_id, payload=payload.model_dump())
    msg = "反馈已记录"
    if result.get("auto_reindexed"):
        msg = "反馈已记录，并已触发自动索引重建"
    return Success(msg=msg, data=result)


@router.post("/upload", summary="上传学习文档")
async def ai_kb_upload(file: UploadFile = File(...)):
    filename = (file.filename or "").strip()
    ext = os.path.splitext(filename)[1].lower()
    if ext not in {".pdf", ".doc", ".docx", ".md", ".txt"}:
        return Fail(code=400, msg="仅支持 pdf/doc/docx/md/txt")

    stored_name = f"{uuid.uuid4().hex}{ext}"
    abs_path = os.path.join(ai_kb_controller.docs_dir, stored_name)
    size = 0
    chunk_size = 1024 * 1024
    conf = await system_setting_controller.get_safe_dict()
    max_upload_size = int(conf.get("ai_kb_max_upload_size") or settings.AI_KB_MAX_UPLOAD_SIZE)
    try:
        with open(abs_path, "wb") as f:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_upload_size:
                    raise ValueError("文件大小超限")
                f.write(chunk)
    except ValueError:
        try:
            os.remove(abs_path)
        except OSError:
            pass
        return Fail(code=400, msg="文件大小超限")
    except OSError as exc:
        try:
            os.remove(abs_path)
        except OSError:
            pass
        return Fail(code=500, msg=f"保存文件失败: {exc}")

    return Success(msg="上传成功", data={"name": filename, "stored_name": stored_name, "size": size})


@router.get("/docs", summary="学习文档列表")
async def ai_kb_docs(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
):
    rows = await ai_kb_controller.list_docs()
    total = len(rows)
    start = (page - 1) * page_size
    end = start + page_size
    return SuccessExtra(data=rows[start:end], total=total, page=page, page_size=page_size)


@router.delete("/docs", summary="删除学习文档")
async def ai_kb_delete_doc(name: str = Query(..., description="存储文件名")):
    ok = await ai_kb_controller.remove_doc(name)
    if not ok:
        return Fail(code=404, msg="文档不存在或删除失败")
    return Success(msg="文档已删除")


@router.post("/reindex", summary="重建知识索引")
async def ai_kb_reindex(incremental: bool = Query(True, description="是否增量重建")):
    data = await ai_kb_controller.rebuild_index(incremental=incremental)
    return Success(msg="索引重建完成", data=data)


@router.post("/reindex_one", summary="单文档重建索引")
async def ai_kb_reindex_one(name: str = Query(..., description="存储文件名")):
    data = await ai_kb_controller.reindex_one_doc(name)
    if not data.get("ok"):
        return Fail(code=400, msg=str(data.get("msg") or "重建失败"))
    return Success(msg="单文档重建完成", data=data)


@router.get("/config", summary="获取AI知识库配置")
async def ai_kb_get_config():
    data = await system_setting_controller.get_safe_dict()
    result = {
        "ai_kb_enabled": bool(data.get("ai_kb_enabled", True)),
        "ai_kb_top_k": int(data.get("ai_kb_top_k") or 5),
        "ai_kb_chunk_size": int(data.get("ai_kb_chunk_size") or 800),
        "ai_kb_chunk_overlap": int(data.get("ai_kb_chunk_overlap") or 120),
        "ai_kb_max_upload_size": int(data.get("ai_kb_max_upload_size") or settings.AI_KB_MAX_UPLOAD_SIZE),
        "ai_kb_feedback_window": int(data.get("ai_kb_feedback_window") or 20),
        "ai_kb_auto_reindex_threshold": int(data.get("ai_kb_auto_reindex_threshold") or 5),
    }
    return Success(data=result)


@router.post("/config", summary="更新AI知识库配置")
async def ai_kb_update_config(payload: AIKbConfigIn):
    await system_setting_controller.update(payload.model_dump())
    return Success(msg="AI知识库配置已保存")


@router.get("/status", summary="AI知识库运行状态")
async def ai_kb_status():
    data = await ai_kb_controller.get_status()
    return Success(data=data)


@router.get("/rebuild_history", summary="重建历史")
async def ai_kb_rebuild_history(limit: int = Query(50, ge=1, le=200)):
    rows = await ai_kb_controller.list_rebuild_history(limit)
    return Success(data=rows)
