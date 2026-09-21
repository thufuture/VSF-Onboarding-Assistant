"""Nạp đội và tài khoản dev: `python -m src.cli.seed_users [--registry DIR]`. Từ chối chạy ở production."""

import argparse
import asyncio
import sys
from pathlib import Path

from src.config import get_settings
from src.infrastructure.persistence.engine import create_engine, create_session_factory
from src.services.auth.seed import DEV_EMAIL_DOMAIN, seed_reference_users

# backend/src/cli/seed_users.py -> gốc repo là parents[3]
_DEFAULT_REGISTRY = Path(__file__).resolve().parents[3] / "docs" / "chatbot-vsf" / "data" / "registry"


async def _run(registry: Path) -> int:
    settings = get_settings()
    if settings.app_env == "production":
        print("Từ chối: không nạp tài khoản dev ở production.", file=sys.stderr)
        return 2
    engine = create_engine(settings.database_url)
    try:
        async with create_session_factory(engine)() as session:
            report = await seed_reference_users(session, registry)
    finally:
        await engine.dispose()
    print(
        f"Đội mới: {report.teams_created}, người dùng mới: {report.users_created}, "
        f"thành viên đội mới: {report.memberships_created} (tài khoản dev dùng miền {DEV_EMAIL_DOMAIN})."
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=_DEFAULT_REGISTRY, help="thư mục registry/*.json")
    args = parser.parse_args()
    sys.exit(asyncio.run(_run(args.registry)))


if __name__ == "__main__":
    main()
