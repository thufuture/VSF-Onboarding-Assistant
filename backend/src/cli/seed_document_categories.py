"""Nạp danh mục tài liệu: `python -m src.cli.seed_document_categories [--registry DIR]`."""

import argparse
import asyncio
import sys
from pathlib import Path

from src.config import get_settings
from src.infrastructure.persistence.engine import create_engine, create_session_factory
from src.services.ingest.category_seed import seed_document_categories

# backend/src/cli/seed_document_categories.py -> gốc repo là parents[3]
_DEFAULT_REGISTRY = Path(__file__).resolve().parents[3] / "docs" / "chatbot-vsf" / "data" / "registry"


async def _run(registry: Path) -> int:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    try:
        async with create_session_factory(engine)() as session:
            report = await seed_document_categories(session, registry)
    finally:
        await engine.dispose()
    print(f"Danh mục mới: {report.created}.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=_DEFAULT_REGISTRY, help="thư mục registry/*.json")
    args = parser.parse_args()
    sys.exit(asyncio.run(_run(args.registry)))


if __name__ == "__main__":
    main()
