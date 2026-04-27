import json
import re
import uuid
from datetime import datetime
from typing import Any, AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.ctx import CTX_USER_ID, CTX_USER_NAME
from app.log import logger
from app.models.admin import AuditLog, User

from .bgtask import BgTasks


class SimpleBaseMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)

        response = await self.before_request(request) or self.app
        await response(request.scope, request.receive, send)
        await self.after_request(request)

    async def before_request(self, request: Request):
        return self.app

    async def after_request(self, request: Request):
        return None


class BackGroundTaskMiddleware(SimpleBaseMiddleware):
    async def before_request(self, request):
        await BgTasks.init_bg_tasks_obj()

    async def after_request(self, request):
        await BgTasks.execute_tasks()


class HttpAuditLogMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, methods: list[str], exclude_paths: list[str]):
        super().__init__(app)
        self.methods = methods
        self.exclude_paths = exclude_paths
        self.exclude_patterns = [re.compile(path, re.I) for path in exclude_paths]
        self.audit_log_paths = ["/api/v1/auditlog/list"]
        self.route_meta_cache: dict[tuple[str, str], tuple[str, str]] = {}
        self.max_route_cache_size = 1024
        self.max_body_size = 1024 * 1024  # 1MB 响应体大小限制

    async def get_request_args(self, request: Request) -> dict:
        args = {}
        # 获取查询参数
        for key, value in request.query_params.items():
            args[key] = value

        # 获取请求体
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.json()
                args.update(body)
            except json.JSONDecodeError:
                try:
                    body = await request.form()
                    # args.update(body)
                    for k, v in body.items():
                        if hasattr(v, "filename"):  # 文件上传行为
                            args[k] = v.filename
                        elif isinstance(v, list) and v and hasattr(v[0], "filename"):
                            args[k] = [file.filename for file in v]
                        else:
                            args[k] = v
                except Exception:
                    pass

        return args

    async def get_response_body(self, request: Request, response: Response) -> Any:
        if request.method == "GET" and response.status_code < 400:
            return None

        content_type = (response.headers.get("content-type") or "").lower()
        if "application/json" not in content_type:
            return {"msg": "Non-JSON response skipped", "content-type": content_type or None}

        # 检查Content-Length
        content_length = response.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.max_body_size:
                    return {"code": 0, "msg": "Response too large to log", "data": None}
            except (TypeError, ValueError):
                pass

        if hasattr(response, "body"):
            body = response.body
        else:
            body_chunks = []
            async for chunk in response.body_iterator:
                if not isinstance(chunk, bytes):
                    chunk = chunk.encode(response.charset)
                body_chunks.append(chunk)

            response.body_iterator = self._async_iter(body_chunks)
            body = b"".join(body_chunks)

        if any(request.url.path.startswith(path) for path in self.audit_log_paths):
            try:
                data = self.lenient_json(body)
                # 只保留基本信息，去除详细的响应内容
                if isinstance(data, dict):
                    data.pop("response_body", None)
                    if "data" in data and isinstance(data["data"], list):
                        for item in data["data"]:
                            item.pop("response_body", None)
                return data
            except Exception:
                return None

        return self.lenient_json(body)

    def lenient_json(self, v: Any) -> Any:
        if isinstance(v, (str, bytes)):
            try:
                return json.loads(v)
            except (ValueError, TypeError):
                if isinstance(v, bytes):
                    v = v.decode("utf-8", errors="ignore")
                return {"raw": str(v)}
        return v

    async def _async_iter(self, items: list[bytes]) -> AsyncGenerator[bytes, None]:
        for item in items:
            yield item

    def _resolve_route_meta(self, app: FastAPI, path: str, method: str) -> tuple[str, str]:
        cache_key = (path, method)
        cached = self.route_meta_cache.get(cache_key)
        if cached is not None:
            return cached

        module = ""
        summary = ""
        for route in app.routes:
            if isinstance(route, APIRoute) and route.path_regex.match(path) and method in route.methods:
                module = ",".join(route.tags)
                summary = route.summary or ""
                break

        if len(self.route_meta_cache) >= self.max_route_cache_size:
            self.route_meta_cache.clear()
        self.route_meta_cache[cache_key] = (module, summary)
        return module, summary

    async def get_request_log(self, request: Request, response: Response) -> dict:
        """
        根据request和response对象获取对应的日志记录数据
        """
        data: dict = {"path": request.url.path, "status": response.status_code, "method": request.method}
        # 路由信息
        app: FastAPI = request.app
        module, summary = self._resolve_route_meta(app, request.url.path, request.method)
        data["module"] = module
        data["summary"] = summary
        # 获取用户信息
        try:
            user_id = CTX_USER_ID.get() or 0
            username = CTX_USER_NAME.get() or ""
            if user_id and not username:
                user_obj = await User.filter(id=user_id).first()
                username = user_obj.username if user_obj else ""
            data["user_id"] = user_id
            data["username"] = username
        except Exception:
            data["user_id"] = 0
            data["username"] = ""
        return data

    async def before_request(self, request: Request):
        request_args = await self.get_request_args(request)
        request.state.request_args = request_args

    async def after_request(self, request: Request, response: Response, process_time: int):
        if request.method in self.methods:
            for pattern in self.exclude_patterns:
                if pattern.search(request.url.path) is not None:
                    return
            data: dict = await self.get_request_log(request=request, response=response)
            data["response_time"] = process_time

            data["request_args"] = request.state.request_args
            data["response_body"] = await self.get_response_body(request, response)
            try:
                await BgTasks.add_task(AuditLog.create, **data)
            except Exception as exc:
                try:
                    await AuditLog.create(**data)
                except Exception:
                    logger.warning(
                        "[http.audit] write failed path={} method={} error={}",
                        request.url.path,
                        request.method,
                        str(exc),
                    )

        return response

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        req_id = uuid.uuid4().hex[:8]
        request.state.req_id = req_id
        logger.info("[http.request] start req_id={} method={} path={} query={}", req_id, request.method, request.url.path, str(request.query_params))
        start_time: datetime = datetime.now()
        await self.before_request(request)
        response = await call_next(request)
        end_time: datetime = datetime.now()
        process_time = int((end_time.timestamp() - start_time.timestamp()) * 1000)
        await self.after_request(request, response, process_time)
        logger.info(
            "[http.request] end req_id={} method={} path={} status={} cost_ms={}",
            req_id,
            request.method,
            request.url.path,
            response.status_code,
            process_time,
        )
        return response
