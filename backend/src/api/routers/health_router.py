"""Health (công khai) và ready (chỉ nội bộ; Caddy chặn từ ngoài ở Phase 1b). Không có route ở gốc."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from src.api.dependencies import get_readiness_service
from src.services.readiness_service import ReadinessService

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Tiến trình còn sống; không chạm DB."""
    return {"status": "ok"}


@router.get("/ready")
async def ready(service: ReadinessService = Depends(get_readiness_service)) -> JSONResponse:
    """DB truy cập được, migration đúng phiên bản, extension bắt buộc có mặt."""
    report = await service.check()
    return JSONResponse(status_code=200 if report.ready else 503, content=report.as_dict())
