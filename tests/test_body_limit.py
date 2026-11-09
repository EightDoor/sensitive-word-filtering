"""请求体上限测试：Content-Length 与实际字节双校验（裸 ASGI 直测）。"""

import asyncio
import json

from sensitive_word_filtering import detector
from sensitive_word_filtering.middleware import MAX_BODY_BYTES

JSON_HEADERS = [(b"content-type", b"application/json")]


def call_app(body_chunks: list[bytes], headers: list[tuple[bytes, bytes]]) -> tuple[int, dict]:
    """直接以 ASGI 协议调用应用，完全控制 Content-Length 与分块方式。"""
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/v1/check",
        "raw_path": b"/api/v1/check",
        "query_string": b"",
        "root_path": "",
        "headers": headers,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "state": {},
    }
    chunks = list(body_chunks)
    sent: list[dict] = []

    async def receive():
        if chunks:
            chunk = chunks.pop(0)
            return {"type": "http.request", "body": chunk, "more_body": bool(chunks)}
        return {"type": "http.disconnect"}

    async def send(message):
        sent.append(message)

    from sensitive_word_filtering.main import app

    asyncio.run(app(scope, receive, send))

    status = next(
        m["status"] for m in sent if m["type"] == "http.response.start"
    )
    body = b"".join(
        m.get("body", b"") for m in sent if m["type"] == "http.response.body"
    )
    return status, json.loads(body) if body else {}


def test_content_length_over_limit(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(detector, "contains", lambda t: calls.append(t) or False)
    headers = JSON_HEADERS + [(b"content-length", str(MAX_BODY_BYTES + 1).encode())]
    status, body = call_app([b"{}"], headers)
    assert status == 413
    assert body["detail"]["code"] == "REQUEST_TOO_LARGE"
    assert calls == []  # 超限不进入检测


def test_non_numeric_content_length_rejected(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(detector, "contains", lambda t: calls.append(t) or False)
    headers = JSON_HEADERS + [(b"content-length", b"abc")]
    status, body = call_app([b"{}"], headers)
    assert status == 413
    assert body["detail"]["code"] == "REQUEST_TOO_LARGE"
    assert calls == []


def test_actual_bytes_over_limit_without_content_length(monkeypatch):
    """无 Content-Length（分块）：按实际累计字节拦截。"""
    calls: list[str] = []
    monkeypatch.setattr(detector, "contains", lambda t: calls.append(t) or False)
    chunks = [b"x" * MAX_BODY_BYTES, b"y"]
    status, body = call_app(chunks, list(JSON_HEADERS))
    assert status == 413
    assert body["detail"]["code"] == "REQUEST_TOO_LARGE"
    assert calls == []


def test_lying_content_length_still_blocked(monkeypatch):
    """谎报 Content-Length：预检放行后仍按实际字节拦截。"""
    calls: list[str] = []
    monkeypatch.setattr(detector, "contains", lambda t: calls.append(t) or False)
    headers = JSON_HEADERS + [(b"content-length", b"5")]
    status, body = call_app([b"x" * (MAX_BODY_BYTES + 1)], headers)
    assert status == 413
    assert body["detail"]["code"] == "REQUEST_TOO_LARGE"
    assert calls == []


def test_exactly_at_limit_passes_middleware(monkeypatch):
    """恰好等于上限不算超限：进入路由后因非法 JSON 返回 422 而非 413。"""
    monkeypatch.setattr(detector, "contains", lambda _t: False)
    headers = JSON_HEADERS + [(b"content-length", str(MAX_BODY_BYTES).encode())]
    status, body = call_app([b"z" * MAX_BODY_BYTES], headers)
    assert status == 422
    assert body["detail"]["code"] == "INVALID_REQUEST"


def test_under_limit_valid_request(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(detector, "contains", lambda t: calls.append(t) or True)
    payload = json.dumps({"text": "代办001工程许可"}).encode()
    headers = JSON_HEADERS + [(b"content-length", str(len(payload)).encode())]
    status, body = call_app([payload], headers)
    assert status == 200
    assert body == {"contains_sensitive_word": True}
    assert calls == ["代办001工程许可"]
