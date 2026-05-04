import json

from fastapi import APIRouter, File, Query, UploadFile

from app.schemas.base import Success
from app.services.skill_know.pack_service import skill_know_pack_service

router = APIRouter()


@router.post("/export", summary="导出知识包")
async def export_pack(category: str | None = Query(None), folder_id: int | None = Query(None)):
    return Success(data=await skill_know_pack_service.export_skills(category=category, folder_id=folder_id))


@router.post("/import", summary="导入知识包")
async def import_pack(file: UploadFile = File(...), skip_duplicates: bool = Query(True)):
    content = await file.read()
    pack_data = json.loads(content.decode("utf-8"))
    return Success(data=await skill_know_pack_service.import_skills(pack_data, skip_duplicates=skip_duplicates))
