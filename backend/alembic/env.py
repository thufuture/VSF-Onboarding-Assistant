import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from src.config import get_settings
from src.model.base import Base

# Từ Phase 2: import các module thực thể ở đây để chúng đăng ký vào Base.metadata (ví dụ `import src.model.user`).

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ConfigParser nội suy "%", nên phải nhân đôi nếu URL có ký tự "%" (mật khẩu mã hóa phần trăm).
config.set_main_option("sqlalchemy.url", get_settings().database_url.replace("%", "%%"))

target_metadata = Base.metadata

# Bảng do extension cài sẵn trong image ParadeDB (PostGIS, ...), không thuộc metadata của ứng dụng. Nếu không loại
# ra, `alembic check` và autogenerate báo nhầm là phải xóa chúng. Thêm tên vào đây nếu image đổi phiên bản.
EXTENSION_MANAGED_TABLES = {"spatial_ref_sys", "_typmod_cache"}


def include_object(object_: object, name: str | None, type_: str, reflected: bool, compare_to: object) -> bool:
    return not (reflected and type_ == "table" and name in EXTENSION_MANAGED_TABLES)


def run_migrations_offline() -> None:
    """Chạy migration ở chế độ offline: chỉ dùng URL, không tạo engine."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, include_object=include_object)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
