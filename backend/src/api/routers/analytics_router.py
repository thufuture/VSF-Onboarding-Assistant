"""`GET /api/v1/portal/analytics` — số liệu cho trang Tổng quan của HR và Admin (biểu đồ đường, cột, tròn, chi phí, độ trễ).

HR chỉ thấy phòng ban của mình; Admin thấy tất cả. Chỉ số liệu tổng hợp, không có nội dung câu hỏi hay tài liệu (INV8).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, require_role
from src.config import Settings, get_settings
from src.dto.response.analytics_response_dto import PortalAnalyticsResponseDTO
from src.model.enums import UserRole
from src.model.user import User
from src.services.portal import analytics_service

router = APIRouter(prefix="/api/v1/portal", tags=["analytics"])


@router.get("/analytics", response_model=PortalAnalyticsResponseDTO)
async def get_analytics(
    user: Annotated[User, Depends(require_role(UserRole.HR, UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    days: Annotated[int, Query(ge=1, le=90)] = 14,
) -> PortalAnalyticsResponseDTO:
    return await analytics_service.build_analytics(db, user, days=days, timezone=settings.app_timezone)
