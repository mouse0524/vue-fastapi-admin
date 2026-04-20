from fastapi.exceptions import (
    HTTPException,
    RequestValidationError,
    ResponseValidationError,
)
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from tortoise.exceptions import DoesNotExist, IntegrityError

from app.log import logger


class SettingNotFound(Exception):
    pass


async def DoesNotExistHandle(req: Request, exc: DoesNotExist) -> JSONResponse:
    logger.warning("[exception.DoesNotExist] path={} query={} exc={}", req.url.path, str(req.query_params), repr(exc))
    content = dict(
        code=404,
        msg=f"Object has not found, exc: {exc}, query_params: {req.query_params}",
    )
    return JSONResponse(content=content, status_code=404)


async def IntegrityHandle(_: Request, exc: IntegrityError) -> JSONResponse:
    logger.exception("[exception.IntegrityError] exc={}", repr(exc))
    content = dict(
        code=500,
        msg=f"IntegrityError，{exc}",
    )
    return JSONResponse(content=content, status_code=500)


async def HttpExcHandle(req: Request, exc: HTTPException) -> JSONResponse:
    logger.warning("[exception.HTTPException] path={} status={} detail={}", req.url.path, exc.status_code, exc.detail)
    content = dict(code=exc.status_code, msg=exc.detail, data=None)
    return JSONResponse(content=content, status_code=exc.status_code)


async def RequestValidationHandle(req: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning("[exception.RequestValidation] path={} exc={}", req.url.path, str(exc))
    content = dict(code=422, msg=f"RequestValidationError, {exc}")
    return JSONResponse(content=content, status_code=422)


async def ResponseValidationHandle(req: Request, exc: ResponseValidationError) -> JSONResponse:
    logger.exception("[exception.ResponseValidation] path={} exc={}", req.url.path, str(exc))
    content = dict(code=500, msg=f"ResponseValidationError, {exc}")
    return JSONResponse(content=content, status_code=500)
