import pytest
from fastapi.middleware.cors import CORSMiddleware

from src.common.base import crear_app

pytestmark = pytest.mark.unit


def _cors_origins(app):
    middleware = next(item for item in app.user_middleware if item.cls is CORSMiddleware)
    return middleware.kwargs["allow_origins"]


def test_cors_denies_cross_origin_requests_by_default(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    assert _cors_origins(crear_app("test", "billing_db")) == []


def test_cors_uses_only_explicit_trimmed_origins(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", " https://portal.example , , http://localhost:3003 ")

    assert _cors_origins(crear_app("test", "billing_db")) == [
        "https://portal.example",
        "http://localhost:3003",
    ]