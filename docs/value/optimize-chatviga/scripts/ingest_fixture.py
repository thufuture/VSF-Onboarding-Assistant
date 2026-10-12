"""Nạp tài liệu thử nghiệm chứa lệnh độc (SYN_E09) vào DB bench `vsf_bench` để đo chèn lệnh GIÁN TIẾP. Chỉ ghi vào DB bench.

Dùng đúng `ingest_document` của sản phẩm (cùng cách cắt mục, chunk, embedding local). File gốc lưu ở thư mục tạm (storage local),
không đẩy lên Cloudinary.

Chạy từ gốc repo:
  PYTHONIOENCODING=utf-8 PYTHONPATH=backend backend/.venv/Scripts/python.exe docs/value/optimize-chatviga/scripts/ingest_fixture.py
"""

import asyncio
import os
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "backend"))

# Embedding local như harness (phải đặt TRƯỚC khi nạp cấu hình); lưu file ở thư mục tạm.
env_text = (ROOT / ".env").read_text(encoding="utf-8")
endpoint = next((line.split("=", 1)[1].strip() for line in env_text.splitlines() if line.startswith("EMBEDDING_ENDPOINT=")), "")
os.environ["EMBEDDING_ENDPOINT"] = endpoint.replace("host.docker.internal", "127.0.0.1")
os.environ["STORAGE_PROVIDER"] = "local"
os.environ["STORAGE_PATH"] = str(Path(tempfile.gettempdir()) / "vsf_bench_storage")

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from src.api import dependencies as deps  # noqa: E402
from src.config import get_settings  # noqa: E402
from src.services.ingest.ingest_service import ingest_document  # noqa: E402

FIXTURE = ROOT / "docs" / "chatbot-vsf" / "data" / "documents" / "injection" / "SYN_E09_FAQ_co_lenh_chen.docx"


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(str(settings.database_url).rsplit("/", 1)[0] + "/vsf_bench")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    embedding = deps.get_embedding_port(settings)
    storage = deps.get_storage_port(settings)
    async with session_factory() as session:
        result = await ingest_document(
            session,
            file_path=FIXTURE,
            category_slug="ho-tro-it",
            owner_email="hr1@vsf-demo.example",
            title="SYN_E09_FAQ_co_lenh_chen",
            source_key="bench-injection-fixture",
            version_label="1.0",
            effective_from=date(2026, 1, 1),
            content_kind="GENERAL",
            confidentiality="INTERNAL",
            embedding=embedding,
            storage=storage,
        )
        await session.commit()
    print(f"đã nạp vào vsf_bench: tài liệu {result.document_id}, phiên bản {result.version_id}, {result.section_count} mục, {result.chunk_count} chunk, mới tạo: {result.created}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
