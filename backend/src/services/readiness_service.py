"""Kiểm tra hệ thống đã sẵn sàng phục vụ chưa (DB, migration, extension). Chỉ dùng nội bộ."""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Ba extension mà thiết kế cần: vector (pgvector), BM25 (ParadeDB), chặn chồng ngày hiệu lực (btree_gist).
REQUIRED_EXTENSIONS: tuple[str, ...] = ("vector", "pg_search", "btree_gist")

# src/services/readiness_service.py -> parents[2] là thư mục chứa alembic.ini (backend/ hoặc /app trong Docker).
_ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


@lru_cache
def migration_heads(alembic_ini: Path = _ALEMBIC_INI) -> tuple[str, ...]:
    """Các revision đầu (head) trong thư mục migration; rỗng nếu chưa có migration nào."""
    script = ScriptDirectory.from_config(Config(str(alembic_ini)))
    return tuple(sorted(script.get_heads()))


@dataclass(frozen=True)
class ReadinessReport:
    ready: bool
    checks: dict[str, dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        return {"status": "ready" if self.ready else "not_ready", "checks": self.checks}


class ReadinessService:
    """Chưa có migration thì chỉ đòi extension "có sẵn"; có migration thì đòi "đã cài" và đúng phiên bản."""

    def __init__(self, session: AsyncSession, heads: tuple[str, ...] | None = None) -> None:
        self._session = session
        self._heads = migration_heads() if heads is None else heads

    async def check(self) -> ReadinessReport:
        try:
            await self._session.execute(text("SELECT 1"))
        except Exception as exc:
            # Chỉ ghi tên loại lỗi: nội dung lỗi có thể chứa máy chủ, cổng hay mật khẩu.
            checks: dict[str, dict[str, Any]] = {
                "database": {"ok": False, "error": type(exc).__name__},
                "migration": {"ok": False},
                "extensions": {"ok": False},
            }
            return ReadinessReport(ready=False, checks=checks)

        checks = {
            "database": {"ok": True},
            "migration": await self._check_migration(),
            "extensions": await self._check_extensions(),
        }
        return ReadinessReport(ready=all(c["ok"] for c in checks.values()), checks=checks)

    async def _check_migration(self) -> dict[str, Any]:
        if not self._heads:
            return {"ok": True, "head": None, "current": None, "note": "chưa có migration"}
        has_table = (
            await self._session.execute(text("SELECT to_regclass('public.alembic_version') IS NOT NULL"))
        ).scalar_one()
        current: tuple[str, ...] = ()
        if has_table:
            rows = await self._session.execute(text("SELECT version_num FROM alembic_version"))
            current = tuple(sorted(row[0] for row in rows))
        return {"ok": current == self._heads, "head": list(self._heads), "current": list(current)}

    async def _check_extensions(self) -> dict[str, Any]:
        names = list(REQUIRED_EXTENSIONS)
        available = await self._names(
            "SELECT name FROM pg_available_extensions WHERE name = ANY(CAST(:names AS text[]))", names
        )
        installed = await self._names(
            "SELECT extname FROM pg_extension WHERE extname = ANY(CAST(:names AS text[]))", names
        )
        required = installed if self._heads else available
        missing = [name for name in REQUIRED_EXTENSIONS if name not in required]
        return {"ok": not missing, "available": sorted(available), "installed": sorted(installed), "missing": missing}

    async def _names(self, sql: str, names: list[str]) -> set[str]:
        result = await self._session.execute(text(sql), {"names": names})
        return {row[0] for row in result}
