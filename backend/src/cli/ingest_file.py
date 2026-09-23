"""Nạp một tài liệu từ bộ dữ liệu giả lập (2-B, CLI-only theo quyết định D4 — xem
docs/chatbot-vsf/plan/phase-2/2-b-nap-tai-lieu-ke-hoach-chi-tiet.md).

Dùng: python -m src.cli.ingest_file D03b [--owner-email hr1@vsf-demo.example]

Đọc sẵn metadata (tiêu đề, danh mục, nhãn phiên bản, ngày hiệu lực) từ
`docs/chatbot-vsf/data/manifests/documents_manifest.csv` theo id truyền vào — không cần nhập tay.
Cần đã chạy trước: `python -m src.cli.seed_document_categories` và `python -m src.cli.seed_users`.
"""

import argparse
import asyncio
import sys
from datetime import date
from pathlib import Path

from src.config import get_settings
from src.infrastructure.persistence.engine import create_engine, create_session_factory
from src.services.ingest.factory import build_embedding_port, build_storage_port
from src.services.ingest.ingest_service import IngestError, ingest_document
from src.services.ingest.registry_lookup import RegistryLookupError, read_manifest_row

# backend/src/cli/ingest_file.py -> gốc repo là parents[3]
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_DATA_DIR = _REPO_ROOT / "docs" / "chatbot-vsf" / "data"
_DEFAULT_MANIFEST = _DEFAULT_DATA_DIR / "manifests" / "documents_manifest.csv"


async def _run(document_id: str, manifest_path: Path, data_dir: Path, owner_email: str) -> int:
    settings = get_settings()
    try:
        row = read_manifest_row(manifest_path, document_id)
    except RegistryLookupError as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 2

    file_path = data_dir / row.relative_path
    embedding = build_embedding_port(settings)
    storage = build_storage_port(settings)

    engine = create_engine(settings.database_url)
    try:
        async with create_session_factory(engine)() as session:
            result = await ingest_document(
                session,
                file_path=file_path,
                category_slug=row.category_slug,
                owner_email=owner_email,
                title=row.title,
                source_key=row.source_key,
                version_label=row.version_label,
                effective_from=date.fromisoformat(row.effective_from),
                content_kind=row.content_kind,
                confidentiality=row.confidentiality,
                embedding=embedding,
                storage=storage,
            )
    except IngestError as exc:
        print(f"Nạp thất bại: {exc}", file=sys.stderr)
        return 1
    finally:
        await engine.dispose()

    trang_thai = "đã có sẵn (bỏ qua, idempotent)" if not result.created else "nạp mới"
    print(
        f"Xong ({trang_thai}): document_id={result.document_id} version_id={result.version_id} "
        f"section={result.section_count} chunk={result.chunk_count} "
        f"model_version={embedding.model_version}"
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document_id", help="ID trong documents_manifest.csv, ví dụ D03b")
    parser.add_argument("--manifest", type=Path, default=_DEFAULT_MANIFEST)
    parser.add_argument("--data-dir", type=Path, default=_DEFAULT_DATA_DIR)
    parser.add_argument("--owner-email", default="hr1@vsf-demo.example")
    args = parser.parse_args()
    sys.exit(asyncio.run(_run(args.document_id, args.manifest, args.data_dir, args.owner_email)))


if __name__ == "__main__":
    main()
