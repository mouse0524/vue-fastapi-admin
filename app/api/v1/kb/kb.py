from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.controllers.kb import kb_controller
from app.core.ctx import CTX_USER_ID
from app.core.dependency import DependAuth
from app.models.admin import User
from app.schemas.base import Success, SuccessExtra
from app.schemas.kb import (
    KbAskIn,
    KbDocumentCreateIn,
    KbDocumentDeleteIn,
    KbFeedbackCreateIn,
    KbSessionCreateIn,
    KbSpaceCreateIn,
    KbSpaceUpdateIn,
)

router = APIRouter(dependencies=[DependAuth])


async def _current_user() -> User:
    user_id = CTX_USER_ID.get()
    user = await User.filter(id=user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="当前用户不存在")
    return user


@router.get("/space/list", summary="知识空间列表")
async def kb_space_list(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    keyword: str | None = Query(None, description="关键字"),
):
    user = await _current_user()
    total, rows = await kb_controller.list_spaces(
        page=page,
        page_size=page_size,
        keyword=keyword,
        owner_id=user.id,
        is_admin=user.is_superuser,
    )
    data = [await item.to_dict() for item in rows]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.post("/space/create", summary="创建知识空间")
async def kb_space_create(payload: KbSpaceCreateIn):
    user = await _current_user()
    data = await kb_controller.create_space(owner_id=user.id, payload=payload.model_dump())
    return Success(msg="创建成功", data=data)


@router.post("/space/update", summary="更新知识空间")
async def kb_space_update(payload: KbSpaceUpdateIn):
    user = await _current_user()
    data = await kb_controller.update_space(owner_id=user.id, payload=payload.model_dump(), is_admin=user.is_superuser)
    return Success(msg="更新成功", data=data)


@router.get("/document/list", summary="知识文档列表")
async def kb_document_list(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    space_id: int | None = Query(None, description="空间ID"),
    keyword: str | None = Query(None, description="关键字"),
    parse_status: str | None = Query(None, description="解析状态"),
    source_type: str | None = Query(None, description="来源类型"),
):
    user = await _current_user()
    total, rows = await kb_controller.list_documents(
        page=page,
        page_size=page_size,
        space_id=space_id,
        keyword=keyword,
        parse_status=parse_status,
        source_type=source_type,
        owner_id=user.id,
        is_admin=user.is_superuser,
    )
    data = [await item.to_dict() for item in rows]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.post("/document/create", summary="创建知识文档")
async def kb_document_create(payload: KbDocumentCreateIn):
    user = await _current_user()
    data = await kb_controller.create_document(owner_id=user.id, payload=payload.model_dump(), is_admin=user.is_superuser)
    return Success(msg="创建成功", data=data)


@router.post("/document/reparse", summary="重解析知识文档")
async def kb_document_reparse(document_id: int = Query(..., description="文档ID")):
    user = await _current_user()
    doc = await kb_controller.reparse_document(document_id=document_id, owner_id=user.id, is_admin=user.is_superuser)
    return Success(msg="重解析完成", data=doc)


@router.post("/document/process_pending", summary="处理待解析知识文档")
async def kb_document_process_pending(document_id: int | None = Query(None, description="文档ID，不传则处理全部待解析")):
    user = await _current_user()
    data = await kb_controller.process_pending_documents(
        owner_id=user.id,
        is_admin=user.is_superuser,
        document_id=document_id,
    )
    return Success(msg="待解析文档处理完成", data=data)


@router.post("/document/delete", summary="删除知识文档")
async def kb_document_delete(payload: KbDocumentDeleteIn):
    user = await _current_user()
    data = await kb_controller.delete_document(document_id=payload.id, owner_id=user.id, is_admin=user.is_superuser)
    return Success(msg="删除成功", data=data)


@router.post("/document/upload", summary="上传知识文档")
async def kb_document_upload(
    space_id: int = Query(..., description="空间ID"),
    title: str | None = Query(None, description="文档标题"),
    file: UploadFile = File(...),
):
    user = await _current_user()
    data = await kb_controller.upload_document(
        owner_id=user.id,
        space_id=space_id,
        title=title,
        file=file,
        is_admin=user.is_superuser,
    )
    return Success(msg="上传成功", data=data)


@router.get("/session/list", summary="会话列表")
async def kb_session_list(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
):
    user = await _current_user()
    total, rows = await kb_controller.list_sessions(user_id=user.id, page=page, page_size=page_size)
    data = [await item.to_dict() for item in rows]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.post("/session/create", summary="创建会话")
async def kb_session_create(payload: KbSessionCreateIn):
    user = await _current_user()
    data = await kb_controller.create_session(user_id=user.id, payload=payload.model_dump(), is_admin=user.is_superuser)
    return Success(msg="创建成功", data=data)


@router.get("/session/messages", summary="会话消息")
async def kb_session_messages(session_id: int = Query(..., description="会话ID")):
    user = await _current_user()
    data = await kb_controller.list_messages(session_id=session_id, user_id=user.id, is_admin=user.is_superuser)
    return Success(data=data)


@router.post("/chat/ask", summary="知识问答")
async def kb_chat_ask(payload: KbAskIn):
    user = await _current_user()
    data = await kb_controller.ask(user_id=user.id, payload=payload.model_dump(), is_admin=user.is_superuser)
    return Success(data=data)


@router.post("/feedback/create", summary="提交反馈")
async def kb_feedback_create(payload: KbFeedbackCreateIn):
    user = await _current_user()
    data = await kb_controller.create_feedback(user_id=user.id, payload=payload.model_dump())
    return Success(msg="反馈提交成功", data=data)


@router.get("/feedback/list", summary="反馈列表")
async def kb_feedback_list(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    status: str | None = Query(None, description="状态"),
):
    total, rows = await kb_controller.list_feedback(page=page, page_size=page_size, status=status)
    data = [await item.to_dict() for item in rows]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/llm/log/list", summary="LLM调用日志")
async def kb_llm_log_list(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    provider: str | None = Query(None, description="模型提供商"),
    model_code: str | None = Query(None, description="模型编码"),
    error_code: str | None = Query(None, description="错误码"),
    session_id: int | None = Query(None, description="会话ID"),
):
    total, rows = await kb_controller.list_llm_logs(
        page=page,
        page_size=page_size,
        provider=provider,
        model_code=model_code,
        error_code=error_code,
        session_id=session_id,
    )
    data = [await item.to_dict() for item in rows]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.get("/llm/test", summary="LLM连通性测试")
async def kb_llm_test():
    data = await kb_controller.test_llm_connectivity()
    return Success(data=data)
