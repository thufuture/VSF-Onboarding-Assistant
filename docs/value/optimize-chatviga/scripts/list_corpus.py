"""Liệt kê tài liệu và số mục trong kho thử `vsf_bench` (bản chụp DB dev dùng cho benchmark)."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "backend"))
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from src.config import get_settings  # noqa: E402


async def main() -> None:
    engine = create_async_engine(str(get_settings().database_url).rsplit("/", 1)[0] + "/vsf_bench")
    async with engine.connect() as conn:
        rows = (await conn.execute(text("""
            SELECT d.title, d.status, count(DISTINCT s.id) AS muc, count(c.id) AS chunk
            FROM documents d JOIN document_versions v ON v.document_id = d.id AND v.status = 'ACTIVE'
            LEFT JOIN document_sections s ON s.version_id = v.id
            LEFT JOIN document_chunks c ON c.version_id = v.id
            GROUP BY d.title, d.status ORDER BY d.title"""))).all()
    for title, status, sections, chunks in rows:
        print(f"{title[:60]:60s} {status:8s} {sections:4d} mục {chunks:4d} chunk")
    await engine.dispose()


asyncio.run(main())
