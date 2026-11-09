"""FastAPI 服务：敏感词布尔检测。

- 启动（lifespan）期初始化自动机，词库异常直接启动失败（fail-closed）。
- 命中是正常 200 结果；错误统一为 {"detail": {"code", "message"}} 且不回显输入。
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import detector
from .errors import (
    INTERNAL_ERROR,
    INTERNAL_ERROR_MESSAGE,
    INVALID_REQUEST,
    INVALID_REQUEST_MESSAGE,
    METHOD_NOT_ALLOWED,
    METHOD_NOT_ALLOWED_MESSAGE,
    NOT_FOUND,
    NOT_FOUND_MESSAGE,
    structured,
)
from .middleware import MAX_BODY_BYTES, BodyLimitMiddleware

logger = logging.getLogger("sensitive_word_filtering")

MAX_TEXT_LENGTH = 10_000


class CheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(max_length=MAX_TEXT_LENGTH)


class CheckResponse(BaseModel):
    contains_sensitive_word: bool


@asynccontextmanager
async def lifespan(_app: FastAPI):
    detector.initialize()
    yield


app = FastAPI(
    title="敏感词检测服务",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(BodyLimitMiddleware, max_bytes=MAX_BODY_BYTES)


@app.post("/api/v1/check", response_model=CheckResponse, summary="检测文本是否包含敏感词")
def check(payload: CheckRequest) -> CheckResponse:
    try:
        return CheckResponse(contains_sensitive_word=detector.contains(payload.text))
    except Exception:
        # 日志只记错误本身，不携带用户输入
        logger.exception("检测执行失败")
        raise HTTPException(
            status_code=500,
            detail={"code": INTERNAL_ERROR, "message": INTERNAL_ERROR_MESSAGE},
        ) from None


@app.get("/health", summary="就绪检查")
def health() -> JSONResponse:
    if not detector.is_ready():
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return JSONResponse(status_code=200, content={"status": "ok"})


@app.exception_handler(RequestValidationError)
async def _validation_error(_request: Request, _exc: RequestValidationError) -> JSONResponse:
    # 固定文案覆盖 FastAPI 默认校验响应，避免 Pydantic 错误回显输入
    return JSONResponse(
        status_code=422,
        content=structured(INVALID_REQUEST, INVALID_REQUEST_MESSAGE),
    )


@app.exception_handler(StarletteHTTPException)
async def _http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and isinstance(exc.detail.get("code"), str):
        content = {"detail": exc.detail}
    elif exc.status_code == 400:
        # FastAPI body 解析失败（含非法 UTF-8 字节）属客户端错误，不冒充服务端错误
        content = structured(INVALID_REQUEST, INVALID_REQUEST_MESSAGE)
    elif exc.status_code == 404:
        content = structured(NOT_FOUND, NOT_FOUND_MESSAGE)
    elif exc.status_code == 405:
        content = structured(METHOD_NOT_ALLOWED, METHOD_NOT_ALLOWED_MESSAGE)
    else:
        content = structured(INTERNAL_ERROR, INTERNAL_ERROR_MESSAGE)
    return JSONResponse(
        status_code=exc.status_code, content=content, headers=exc.headers
    )


@app.exception_handler(Exception)
async def _unhandled(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("未处理异常")
    return JSONResponse(
        status_code=500,
        content=structured(INTERNAL_ERROR, INTERNAL_ERROR_MESSAGE),
    )
