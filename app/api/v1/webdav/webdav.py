from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.core.ctx import CTX_USER_ID
from app.core.dependency import DependAuth
from app.controllers.webdav import webdav_controller
from app.log import logger
from app.models.admin import User
from app.schemas.base import Success, SuccessExtra
from app.schemas.webdav import WebDavShareCreateIn, WebDavShareDeleteIn
from app.utils.http_headers import build_download_content_disposition

router = APIRouter(dependencies=[DependAuth])
public_router = APIRouter()


@router.get("/list", summary="WebDAV文件列表")
async def list_webdav(path: str = Query("/", description="目录路径")):
    logger.info("[api.webdav.list] request path={}", path)
    rows = await webdav_controller.list_dir(path)
    logger.info("[api.webdav.list] response path={} count={}", path, len(rows))
    return Success(data=rows)


@router.post("/share/create", summary="创建WebDAV分享")
async def create_webdav_share(payload: WebDavShareCreateIn):
    user_id = CTX_USER_ID.get()
    data = await webdav_controller.create_share(
        file_path=payload.file_path,
        file_name=payload.file_name,
        created_by=user_id,
        expire_hours=payload.expire_hours,
    )
    return Success(msg="分享创建成功", data=data)


@router.get("/share/list", summary="WebDAV分享记录")
async def list_webdav_shares(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    include_history: bool = Query(False, description="是否包含历史记录(已失效/已过期)"),
):
    user_id = CTX_USER_ID.get()
    user = await User.filter(id=user_id).first()
    is_admin = bool(user and user.is_superuser)
    created_by = None if is_admin else user_id
    total, rows = await webdav_controller.list_shares(
        created_by=created_by,
        page=page,
        page_size=page_size,
        include_history=include_history,
    )
    user_ids = {item.created_by for item in rows}
    user_map: dict[int, str] = {}
    if user_ids:
        users = await User.filter(id__in=list(user_ids)).values("id", "alias", "username")
        user_map = {u["id"]: (u.get("alias") or u.get("username") or "") for u in users}
    data = []
    for item in rows:
        item_dict = await item.to_dict()
        item_dict["creator_name"] = user_map.get(item.created_by, "")
        data.append(item_dict)
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.post("/share/delete", summary="删除WebDAV分享记录")
async def delete_webdav_share(payload: WebDavShareDeleteIn):
    user_id = CTX_USER_ID.get()
    user = await User.filter(id=user_id).first()
    is_admin = bool(user and user.is_superuser)
    await webdav_controller.delete_share(payload.id, None if is_admin else user_id)
    return Success(msg="删除成功")


@public_router.get("/share/download", summary="公开下载WebDAV分享文件")
async def webdav_share_download(code: str = Query(..., description="分享码")):
    share = await webdav_controller.get_share(code)
    iterator, headers = await webdav_controller.download_stream(share.file_path)
    content_type = headers.get("content-type") or "application/octet-stream"
    disposition = build_download_content_disposition(share.file_name)
    logger.info("[webdav.share.download] code={} file_path={}", code, share.file_path)
    return StreamingResponse(
        iterator(),
        media_type=content_type,
        headers={"Content-Disposition": disposition},
    )
