import json
import uuid

from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import StreamingResponse

from app.schemas.base import Success
from app.services.skill_know.document_service import skill_know_document_service

router = APIRouter()

_TASKS: dict[str, dict] = {}


@router.post("/batch", summary="批量上传文档并转换Skill")
async def batch_upload(files: list[UploadFile] = File(...), folder_id: int | None = Query(None), use_llm: bool = Query(True)):
    task_id = str(uuid.uuid4())
    task = {"task_id": task_id, "status": "running", "total": len(files), "completed": 0, "failed": 0, "files": []}
    _TASKS[task_id] = task
    for file in files:
        item = {"filename": file.filename, "status": "processing", "progress": 10, "message": "上传解析中"}
        task["files"].append(item)
        try:
            doc = await skill_know_document_service.upload(file, folder_id=folder_id)
            item.update({"status": "completed", "progress": 100, "message": "处理完成", "result": doc})
            task["completed"] += 1
        except Exception as exc:
            item.update({"status": "failed", "progress": 100, "message": "处理失败", "error": str(exc)})
            task["failed"] += 1
    task["status"] = "completed"
    return Success(data={"task_id": task_id, "file_count": len(files), "stream_url": f"/api/v1/skill-know/upload/tasks/{task_id}/stream"})


@router.get("/tasks/get", summary="获取批量上传任务")
async def get_task(task_id: str = Query(...)):
    return Success(data=_TASKS.get(task_id) or {"task_id": task_id, "status": "missing", "files": []})


@router.get("/tasks/stream", summary="批量上传任务SSE")
async def stream_task(task_id: str = Query(...)):
    async def generate():
        task = _TASKS.get(task_id) or {"task_id": task_id, "status": "missing", "files": []}
        for file in task.get("files", []):
            yield f"event: file.progress\ndata: {json.dumps(file, ensure_ascii=False)}\n\n"
        yield f"event: task.completed\ndata: {json.dumps(task, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.delete("/tasks/delete", summary="清理批量上传任务")
async def cleanup_task(task_id: str = Query(...)):
    _TASKS.pop(task_id, None)
    return Success(msg="清理成功")
