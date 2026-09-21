import json
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.readiness_service import REQUIRED_EXTENSIONS, ReadinessService, migration_heads

_ALL = set(REQUIRED_EXTENSIONS)


class _FakeResult:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self._rows = rows

    def __iter__(self) -> Any:
        return iter(self._rows)

    def scalar_one(self) -> Any:
        return self._rows[0][0]


class _FakeSession:
    """Giả lập AsyncSession đủ cho ReadinessService; nhận diện câu SQL theo từ khóa."""

    def __init__(
        self,
        *,
        fail: bool = False,
        available: set[str] | None = None,
        installed: set[str] | None = None,
        alembic_table: bool = True,
        versions: tuple[str, ...] = (),
    ) -> None:
        self.fail = fail
        self.available = _ALL if available is None else available
        self.installed = {"vector", "pg_search"} if installed is None else installed
        self.alembic_table = alembic_table
        self.versions = versions

    async def execute(self, statement: Any, params: dict[str, Any] | None = None) -> _FakeResult:
        if self.fail:
            raise ConnectionRefusedError("host=secret-db port=5432 password=hunter2")
        sql = str(statement)
        if "to_regclass" in sql:
            return _FakeResult([(self.alembic_table,)])
        if "alembic_version" in sql:
            return _FakeResult([(v,) for v in self.versions])
        if "pg_available_extensions" in sql:
            return _FakeResult([(n,) for n in self.available])
        if "pg_extension" in sql:
            return _FakeResult([(n,) for n in self.installed])
        return _FakeResult([(1,)])


def _service(session: _FakeSession, heads: tuple[str, ...] = ()) -> ReadinessService:
    return ReadinessService(cast(AsyncSession, session), heads=heads)


async def test_ready_without_migrations_only_needs_extensions_to_be_available() -> None:
    report = await _service(_FakeSession(installed={"vector"})).check()
    assert report.ready
    assert report.checks["migration"]["note"] == "chưa có migration"
    assert report.checks["extensions"]["available"] == sorted(_ALL)


async def test_not_ready_when_database_is_down_and_no_error_text_leaks() -> None:
    report = await _service(_FakeSession(fail=True)).check()
    assert not report.ready
    assert report.checks["database"] == {"ok": False, "error": "ConnectionRefusedError"}
    assert "hunter2" not in json.dumps(report.as_dict())
    assert "secret-db" not in json.dumps(report.as_dict())


async def test_not_ready_when_an_extension_is_not_available() -> None:
    report = await _service(_FakeSession(available={"vector", "pg_search"})).check()
    assert not report.ready
    assert report.checks["extensions"]["missing"] == ["btree_gist"]


async def test_with_migrations_extensions_must_be_installed() -> None:
    session = _FakeSession(installed={"vector", "pg_search"}, versions=("0001",))
    report = await _service(session, heads=("0001",)).check()
    assert report.checks["migration"]["ok"]
    assert not report.checks["extensions"]["ok"]
    assert report.checks["extensions"]["missing"] == ["btree_gist"]
    assert not report.ready


async def test_ready_with_migrations_at_head_and_all_extensions_installed() -> None:
    session = _FakeSession(installed=set(_ALL), versions=("0001",))
    report = await _service(session, heads=("0001",)).check()
    assert report.ready


async def test_not_ready_when_migration_version_differs_from_head() -> None:
    session = _FakeSession(installed=set(_ALL), versions=("0000",))
    report = await _service(session, heads=("0001",)).check()
    assert not report.checks["migration"]["ok"]
    assert report.checks["migration"]["current"] == ["0000"]
    assert not report.ready


async def test_not_ready_when_alembic_version_table_is_missing() -> None:
    session = _FakeSession(installed=set(_ALL), alembic_table=False)
    report = await _service(session, heads=("0001",)).check()
    assert not report.checks["migration"]["ok"]
    assert report.checks["migration"]["current"] == []


def test_migration_heads_reads_the_alembic_directory() -> None:
    assert isinstance(migration_heads(), tuple)
