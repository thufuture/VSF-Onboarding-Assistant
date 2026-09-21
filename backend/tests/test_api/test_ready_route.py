from typing import Any

import httpx

from src.api.dependencies import get_readiness_service
from src.main import create_app
from src.services.readiness_service import ReadinessReport


class _FakeService:
    def __init__(self, report: ReadinessReport) -> None:
        self._report = report

    async def check(self) -> ReadinessReport:
        return self._report


async def _get_ready(report: ReadinessReport) -> httpx.Response:
    app = create_app()
    app.dependency_overrides[get_readiness_service] = lambda: _FakeService(report)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        return await client.get("/api/v1/ready")


async def test_ready_returns_200_when_ready() -> None:
    checks: dict[str, dict[str, Any]] = {"database": {"ok": True}}
    response = await _get_ready(ReadinessReport(ready=True, checks=checks))
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": checks}


async def test_ready_returns_503_when_not_ready() -> None:
    checks: dict[str, dict[str, Any]] = {"database": {"ok": False, "error": "ConnectionRefusedError"}}
    response = await _get_ready(ReadinessReport(ready=False, checks=checks))
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
