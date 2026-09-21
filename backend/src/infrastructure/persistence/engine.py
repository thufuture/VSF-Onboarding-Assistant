"""Engine và session factory bất đồng bộ cho PostgreSQL (asyncpg)."""

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


def create_engine(database_url: str) -> AsyncEngine:
    # pool_pre_ping: kiểm tra kết nối trước khi dùng, để DB khởi động lại không làm request đầu tiên lỗi.
    return create_async_engine(database_url, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
