import os
import subprocess
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

BACKEND_DIR = Path(__file__).resolve().parents[2]


def _test_database_url() -> str:
    url = os.environ.get("VSF_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Đặt VSF_TEST_DATABASE_URL (PostgreSQL/ParadeDB thật) để chạy test tích hợp")
    return url


@pytest.fixture(scope="session")
def migrated_database_url() -> str:
    """Đưa DB test lên `head` (chạy lại vẫn an toàn) để test không phụ thuộc thứ tự chạy."""
    url = _test_database_url()
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env={**os.environ, "DATABASE_URL": url},
        check=True,
        capture_output=True,
    )
    return url


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    eng = create_async_engine(_test_database_url())
    try:
        yield eng
    finally:
        await eng.dispose()


@pytest.fixture
async def conn(migrated_database_url: str) -> AsyncIterator[AsyncConnection]:
    """Kết nối trong một transaction luôn bị hoàn tác: test ghi dữ liệu thoải mái mà không để lại gì."""
    eng = create_async_engine(migrated_database_url)
    try:
        async with eng.connect() as connection:
            transaction = await connection.begin()
            try:
                yield connection
            finally:
                await transaction.rollback()
    finally:
        await eng.dispose()
