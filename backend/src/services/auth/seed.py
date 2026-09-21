"""Nạp đội và tài khoản dev từ `docs/chatbot-vsf/data/registry/*.json`. Chỉ dùng ngoài production."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.model.team import Team
from src.model.team_member import TeamMember
from src.model.user import User
from src.services.auth.auth_service import normalize_email
from src.services.auth.passwords import hash_password

# Mọi tài khoản dev đều thuộc miền này; production từ chối khởi động nếu còn bất kỳ tài khoản nào như vậy.
DEV_EMAIL_DOMAIN = "@vsf-demo.example"


@dataclass
class SeedReport:
    teams_created: int = 0
    users_created: int = 0
    memberships_created: int = 0


def _load(registry_dir: Path, name: str) -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], json.loads((registry_dir / name).read_text(encoding="utf-8")))


async def seed_reference_users(session: AsyncSession, registry_dir: Path) -> SeedReport:
    """Tạo đội, người dùng và thành viên đội từ registry. Chạy lại không nhân đôi và không đổi mật khẩu đã có."""
    report = SeedReport()

    teams: dict[str, Team] = {}
    for item in _load(registry_dir, "teams.json"):
        team = await session.scalar(select(Team).where(Team.code == item["code"]))
        if team is None:
            team = Team(
                code=item["code"],
                name=item["name"],
                ticket_prefix=item.get("ticket_prefix"),
                description=item.get("description"),
            )
            session.add(team)
            report.teams_created += 1
        teams[item["code"]] = team
    await session.flush()

    for item in _load(registry_dir, "users.json"):
        email = normalize_email(item["email"])
        user = await session.scalar(select(User).where(func.lower(User.email) == email))
        if user is None:
            user = User(
                email=email,
                display_name=item["display_name"],
                role=item["role"],
                password_hash=hash_password(item["password_dev_only"]),
            )
            session.add(user)
            report.users_created += 1
        await session.flush()
        for code in item.get("teams", []):
            team = teams[code]
            existing = await session.get(TeamMember, (team.id, user.id))
            if existing is None:
                session.add(TeamMember(team_id=team.id, user_id=user.id))
                report.memberships_created += 1
    await session.commit()
    return report


async def count_dev_accounts(session: AsyncSession) -> int:
    result = await session.scalar(
        select(func.count()).select_from(User).where(func.lower(User.email).like(f"%{DEV_EMAIL_DOMAIN}"))
    )
    return int(result or 0)


async def assert_no_dev_accounts(session: AsyncSession) -> None:
    """Production không được chạy khi còn tài khoản dev (mật khẩu dev nằm trong repo)."""
    found = await count_dev_accounts(session)
    if found:
        raise RuntimeError(
            f"Còn {found} tài khoản dev ({DEV_EMAIL_DOMAIN}) trong cơ sở dữ liệu: xóa chúng trước khi chạy production."
        )
