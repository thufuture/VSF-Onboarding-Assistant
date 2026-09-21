"""Phụ thuộc dùng chung cho router (mở session DB, dựng service)."""

from collections.abc import AsyncIterator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.services.readiness_service import ReadinessService


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with factory() as session:
        yield session


def get_readiness_service(session: AsyncSession = Depends(get_db)) -> ReadinessService:
    return ReadinessService(session)
