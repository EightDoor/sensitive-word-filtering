"""请求体大小上限中间件：Content-Length 与实际接收字节双校验。

只查 Content-Length 会被分块传输/缺头请求绕过；只查实际字节则超大体
已先被完整接收。做法：预读完整请求体（上限 128 KiB，缓冲安全），
两条路径任一超限即返回结构化 413，应用在超限场景下完全不被调用。

不采用「包装 receive 抛异常」方案：FastAPI 路由会把 body 读取期的任何异常
包装成 HTTPException(400, "There was an error parsing the body")，信号无法穿出。
"""
from __future__ import annotations

from fastapi.responses import JSONResponse
from starlette.datastructures import Headers

from .errors import REQUEST_TOO_LARGE, REQUEST_TOO_LARGE_MESSAGE, structured

MAX_BODY_BYTES = 128 * 1024


class BodyLimitMiddleware:
    def __init__(self, app, max_bytes: int = MAX_BODY_BYTES):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Content-Length 预检：非数字或超限直接拒绝
        content_length = Headers(scope=scope).get("content-length")
        if content_length is not None:
            try:
                length = int(content_length)
            except ValueError:
                length = -1  # 非法头按超限处理，不当作合法长度
            if length < 0 or length > self.max_bytes:
                await self._send_413(scope, receive, send)
                return

        # 实际字节预读：覆盖无 Content-Length 与谎报长度的请求
        body = b""
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                break
            if message["type"] != "http.request":
                continue
            body += message.get("body", b"")
            if len(body) > self.max_bytes:
                await self._send_413(scope, receive, send)
                return
            if not message.get("more_body", False):
                break

        # 把已缓冲的 body 重放给应用，一次性投递后模拟断连
        replayed = False

        async def replay_receive():
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": body, "more_body": False}
            return {"type": "http.disconnect"}

        await self.app(scope, replay_receive, send)

    async def _send_413(self, scope, receive, send) -> None:
        response = JSONResponse(
            status_code=413,
            content=structured(REQUEST_TOO_LARGE, REQUEST_TOO_LARGE_MESSAGE),
        )
        await response(scope, receive, send)
