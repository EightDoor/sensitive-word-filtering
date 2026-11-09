"""API 契约测试：布尔结果、严格校验、结构化错误与健康检查。"""

import pytest
from fastapi.testclient import TestClient

from sensitive_word_filtering import detector
from sensitive_word_filtering.main import MAX_TEXT_LENGTH, app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_check_hit(client):
    resp = client.post("/api/v1/check", json={"text": "代办001工程许可"})
    assert resp.status_code == 200
    assert resp.json() == {"contains_sensitive_word": True}


def test_check_miss(client):
    resp = client.post("/api/v1/check", json={"text": "请问明天天气怎么样"})
    assert resp.status_code == 200
    assert resp.json() == {"contains_sensitive_word": False}


def test_empty_text_accepted(client):
    resp = client.post("/api/v1/check", json={"text": ""})
    assert resp.status_code == 200
    assert resp.json() == {"contains_sensitive_word": False}


def test_boundary_length_accepted(client):
    resp = client.post("/api/v1/check", json={"text": "你" * MAX_TEXT_LENGTH})
    assert resp.status_code == 200
    assert isinstance(resp.json()["contains_sensitive_word"], bool)


def test_over_boundary_rejected(client):
    resp = client.post("/api/v1/check", json={"text": "你" * (MAX_TEXT_LENGTH + 1)})
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_REQUEST"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"text": None},
        {"text": 12345},
        {"text": ["代办001工程许可"]},
        {"text": "正常", "extra": "SECRET_MARKER_XYZ"},
    ],
)
def test_invalid_fields_rejected_structured(client, payload):
    resp = client.post("/api/v1/check", json=payload)
    assert resp.status_code == 422
    body = resp.json()
    assert body["detail"]["code"] == "INVALID_REQUEST"
    assert body["detail"]["message"]
    # 响应不回显输入
    assert "SECRET_MARKER_XYZ" not in resp.text
    assert "12345" not in resp.text


def test_malformed_json_rejected(client):
    resp = client.post(
        "/api/v1/check", content="{", headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_REQUEST"



def test_invalid_utf8_body_structured_client_error(client):
    """非 UTF-8 字节的 JSON 体：400 + INVALID_REQUEST，不冒充服务端错误、不回显字节。"""
    resp = client.post(
        "/api/v1/check",
        content=b'{"text":"\xff\xfe\xfa"}',
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["detail"]["code"] == "INVALID_REQUEST"
    assert resp.content.find(b"\xff") == -1

def test_detection_error_returns_500_not_false(client, monkeypatch):
    def _boom(_text):
        raise RuntimeError("检测器故障")

    monkeypatch.setattr(detector, "contains", _boom)
    resp = client.post("/api/v1/check", json={"text": "任意内容"})
    assert resp.status_code == 500
    body = resp.json()
    assert body["detail"]["code"] == "INTERNAL_ERROR"
    assert "contains_sensitive_word" not in resp.text
    assert "任意内容" not in resp.text


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_health_503_when_not_initialized(monkeypatch):
    monkeypatch.setattr(detector, "_automaton", None)
    # 不进入 context manager：lifespan 不执行，检测器保持未初始化
    raw_client = TestClient(app)
    assert raw_client.get("/health").status_code == 503


def test_check_without_startup_returns_500_not_false(monkeypatch):
    monkeypatch.setattr(detector, "_automaton", None)
    raw_client = TestClient(app)
    resp = raw_client.post("/api/v1/check", json={"text": "你好"})
    assert resp.status_code == 500
    assert resp.json()["detail"]["code"] == "INTERNAL_ERROR"
    assert "contains_sensitive_word" not in resp.text


def test_startup_fails_when_dictionary_empty(monkeypatch):
    monkeypatch.setattr(detector, "_automaton", None)
    monkeypatch.setattr(detector, "_load_words", lambda: [])
    with pytest.raises(RuntimeError):
        with TestClient(app):
            pass


def test_openapi_exposes_paths(client):
    spec = client.get("/openapi.json").json()
    assert "/api/v1/check" in spec["paths"]
    assert "/health" in spec["paths"]


def test_unknown_path_structured_404(client):
    resp = client.get("/no-such-path")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "NOT_FOUND"


def test_wrong_method_structured_405(client):
    resp = client.get("/api/v1/check")
    assert resp.status_code == 405
    assert resp.json()["detail"]["code"] == "METHOD_NOT_ALLOWED"
