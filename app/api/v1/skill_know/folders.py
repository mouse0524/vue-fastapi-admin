from fastapi import APIRouter, Query

from app.schemas.base import Success
from app.schemas.skill_know import SkillKnowFolderIn, SkillKnowFolderUpdate
from app.services.skill_know.folder_service import skill_know_folder_service

router = APIRouter()


@router.get("/list", summary="文件夹列表")
async def list_folders(parent_id: int | None = Query(None), tree: bool = Query(False)):
    return Success(data=await skill_know_folder_service.list(parent_id=parent_id, tree=tree))


@router.post("/create", summary="创建文件夹")
async def create_folder(payload: SkillKnowFolderIn):
    return Success(data=await skill_know_folder_service.create(payload))


@router.post("/update", summary="更新文件夹")
async def update_folder(payload: SkillKnowFolderUpdate):
    return Success(data=await skill_know_folder_service.update(payload))


@router.delete("/delete", summary="删除文件夹")
async def delete_folder(folder_id: int = Query(...)):
    await skill_know_folder_service.delete(folder_id)
    return Success(msg="删除成功")
