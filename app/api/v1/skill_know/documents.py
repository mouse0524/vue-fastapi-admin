from fastapi import APIRouter, File, Query, UploadFile

from app.models.enums import SkillKnowDocumentStatus
from app.schemas.base import Success, SuccessExtra
from app.schemas.skill_know import SkillKnowBatchConvertIn, SkillKnowConvertIn, SkillKnowDocumentUpdate, SkillKnowMoveIn
from app.services.skill_know.document_service import skill_know_document_service

router = APIRouter()


@router.post("/upload", summary="上传文档")
async def upload_document(file: UploadFile = File(...), title: str | None = None, folder_id: int | None = None):
    return Success(data=await skill_know_document_service.upload(file, title=title, folder_id=folder_id))


@router.get("/list", summary="文档列表")
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    folder_id: int | None = Query(None),
    category: str | None = Query(None),
    status: SkillKnowDocumentStatus | None = Query(None),
    is_converted: bool | None = Query(None),
):
    total, rows = await skill_know_document_service.list(
        page=page,
        page_size=page_size,
        folder_id=folder_id,
        category=category,
        status=status,
        is_converted=is_converted,
    )
    return SuccessExtra(data=rows, total=total, page=page, page_size=page_size)


@router.get("/get", summary="文档详情")
async def get_document(document_id: int = Query(...)):
    return Success(data=await skill_know_document_service.get(document_id))


@router.post("/update", summary="更新文档")
async def update_document(payload: SkillKnowDocumentUpdate):
    return Success(data=await skill_know_document_service.update(payload))


@router.delete("/delete", summary="删除文档")
async def delete_document(document_id: int = Query(...)):
    await skill_know_document_service.delete(document_id)
    return Success(msg="删除成功")


@router.post("/move", summary="移动文档")
async def move_document(payload: SkillKnowMoveIn):
    return Success(data=await skill_know_document_service.move(payload.target_id, payload.folder_id))


@router.post("/convert-to-skill", summary="文档转Skill")
async def convert_to_skill(payload: SkillKnowConvertIn):
    return Success(data=await skill_know_document_service.convert_to_skill(
        payload.document_id,
        use_llm=payload.use_llm,
        auto_activate=payload.auto_activate,
        folder_id=payload.folder_id,
    ))


@router.post("/batch-convert", summary="批量文档转Skill")
async def batch_convert_to_skill(payload: SkillKnowBatchConvertIn):
    results = []
    for document_id in payload.document_ids:
        try:
            data = await skill_know_document_service.convert_to_skill(document_id, use_llm=payload.use_llm, folder_id=payload.folder_id)
            results.append({"document_id": document_id, "success": True, "skill": data.get("skill")})
        except Exception as exc:
            results.append({"document_id": document_id, "success": False, "error": str(exc)})
    return Success(data={"total": len(results), "success_count": sum(1 for item in results if item["success"]), "results": results})


@router.get("/search", summary="搜索文档")
async def search_documents(q: str = Query(...), limit: int = Query(20, ge=1, le=100)):
    rows = await skill_know_document_service.search(q, limit=limit)
    return Success(data={"items": rows, "total": len(rows)})
