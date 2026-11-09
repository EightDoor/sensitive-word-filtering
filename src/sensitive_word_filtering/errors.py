"""结构化错误码与固定安全文案。

响应与日志统一走这里的常量：错误响应只含错误码与固定文案，
不回显请求正文、命中词或校验失败的原始输入。
"""

from __future__ import annotations

INVALID_REQUEST = "INVALID_REQUEST"
REQUEST_TOO_LARGE = "REQUEST_TOO_LARGE"
INTERNAL_ERROR = "INTERNAL_ERROR"
NOT_FOUND = "NOT_FOUND"
METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"

INVALID_REQUEST_MESSAGE = "请求参数不合法，请检查后重试"
REQUEST_TOO_LARGE_MESSAGE = "请求体超过大小限制，请减少内容后重试"
INTERNAL_ERROR_MESSAGE = "服务内部错误，请稍后重试"
NOT_FOUND_MESSAGE = "请求的资源不存在"
METHOD_NOT_ALLOWED_MESSAGE = "请求方法不被允许"


def structured(code: str, message: str) -> dict:
    """构造统一错误响应体 {"detail": {"code", "message"}}。"""
    return {"detail": {"code": code, "message": message}}
