import os
from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    url = os.environ.get("VSF_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Đặt VSF_TEST_DATABASE_URL (PostgreSQL/ParadeDB thật) để chạy test tích hợp")
    eng = create_async_engine(url)
    try:
        yield eng
    finally:
        await eng.dispose()
