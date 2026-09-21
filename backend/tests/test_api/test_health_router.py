import httpx
import pytest
from fastapi import FastAPI

from src.config import get_settings
from src.main import create_app


def _client(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_health_is_ok_and_needs_no_database() -> None:
    async with _client(create_app()) as client:
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_request_id_is_generated_when_missing() -> None:
    async with _client(create_app()) as client:
        response = await client.get("/api/v1/health")
    request_id = response.headers["X-Request-ID"]
    assert len(request_id) == 32
    assert request_id.isalnum()


async def test_valid_request_id_from_client_is_echoed() -> None:
    async with _client(create_app()) as client:
        response = await client.get("/api/v1/health", headers={"X-Request-ID": "trace-abc_123.x"})
    assert response.headers["X-Request-ID"] == "trace-abc_123.x"


async def test_invalid_request_id_is_replaced() -> None:
    async with _client(create_app()) as client:
        response = await client.get("/api/v1/health", headers={"X-Request-ID": "has space"})
    assert response.headers["X-Request-ID"] != "has space"
    assert len(response.headers["X-Request-ID"]) == 32


@pytest.mark.parametrize("path", ["/health", "/ready", "/api/health", "/api/ready"])
async def test_there_are_no_routes_at_the_root_or_without_version(path: str) -> None:
    async with _client(create_app()) as client:
        response = await client.get(path)
    assert response.status_code == 404


async def test_api_docs_are_disabled_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    try:
        async with _client(create_app()) as client:
            docs = await client.get("/api/docs")
            schema = await client.get("/api/openapi.json")
    finally:
        get_settings.cache_clear()
    assert docs.status_code == 404
    assert schema.status_code == 404


async def test_api_docs_are_available_in_development(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    get_settings.cache_clear()
    try:
        async with _client(create_app()) as client:
            docs = await client.get("/api/docs")
    finally:
        get_settings.cache_clear()
    assert docs.status_code == 200
