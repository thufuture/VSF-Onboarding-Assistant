"""Kiểm tra trên PostgreSQL/ParadeDB thật: readiness, ba extension, ràng buộc chống chồng ngày hiệu lực."""

import uuid
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from src.infrastructure.persistence.engine import create_session_factory
from src.services.readiness_service import REQUIRED_EXTENSIONS, ReadinessService

pytestmark = pytest.mark.integration


async def test_readiness_against_a_real_database(engine: AsyncEngine) -> None:
    async with create_session_factory(engine)() as session:
        report = await ReadinessService(session, heads=()).check()
    assert report.ready, report.as_dict()
    assert set(report.checks["extensions"]["available"]) == set(REQUIRED_EXTENSIONS)


async def test_exclusion_constraint_rejects_overlapping_active_versions(engine: AsyncEngine) -> None:
    # Thiết kế (INV1/INV17) dựa vào EXCLUDE USING gist + btree_gist để hai bản ACTIVE của cùng code không chồng ngày.
    schema = f"vsf_test_{uuid.uuid4().hex[:8]}"
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist"))
        await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        await conn.execute(
            text(
                f"""CREATE TABLE "{schema}".versions (
                    code text, valid_from date, valid_to date, status text,
                    CONSTRAINT ex_no_overlap EXCLUDE USING gist
                        (code WITH =, daterange(valid_from, valid_to, '[]') WITH &&)
                        WHERE (status = 'ACTIVE'))"""
            )
        )
    insert = text(f'INSERT INTO "{schema}".versions VALUES (:code, :valid_from, :valid_to, :status)')

    async def add(valid_from: date, valid_to: date, status: str) -> None:
        async with engine.begin() as conn:
            await conn.execute(insert, {"code": "A", "valid_from": valid_from, "valid_to": valid_to, "status": status})

    try:
        await add(date(2024, 1, 1), date(2024, 12, 31), "ACTIVE")
        with pytest.raises(IntegrityError):
            await add(date(2024, 6, 1), date(2025, 6, 1), "ACTIVE")  # chồng ngày, cùng ACTIVE: bị từ chối
        await add(date(2025, 1, 1), date(2025, 12, 31), "ACTIVE")  # không chồng: được
        await add(date(2024, 6, 1), date(2025, 6, 1), "ARCHIVED")  # chồng nhưng không ACTIVE: được
    finally:
        async with engine.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
