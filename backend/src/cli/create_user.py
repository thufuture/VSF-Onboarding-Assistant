"""Tạo tài khoản thật (dùng được ở production): `python -m src.cli.create_user --email E --name N [--role ADMIN]`.

Mật khẩu được hỏi lúc chạy (không nhận qua tham số dòng lệnh để không lọt vào lịch sử shell / repo).
Từ chối email miền dev vì production không khởi động nếu còn tài khoản dev.
"""

import argparse
import asyncio
import getpass
import secrets
import sys

from sqlalchemy import func, select

from src.config import get_settings
from src.infrastructure.persistence.engine import create_engine, create_session_factory
from src.model.enums import UserRole
from src.model.team import Team
from src.model.team_member import TeamMember
from src.model.user import User
from src.services.auth.auth_service import normalize_email
from src.services.auth.passwords import hash_password
from src.services.auth.seed import DEV_EMAIL_DOMAIN

MIN_PASSWORD_LENGTH = 12


def validate(email: str, password: str) -> str | None:
    """Trả về thông báo lỗi, hoặc None nếu hợp lệ."""
    if "@" not in email or email.endswith("@"):
        return "Email không hợp lệ."
    if email.endswith(DEV_EMAIL_DOMAIN):
        return f"Không dùng email miền dev {DEV_EMAIL_DOMAIN}."
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Mật khẩu tối thiểu {MIN_PASSWORD_LENGTH} ký tự."
    return None


async def _run(email: str, name: str, role: str, password: str, team_code: str | None = None) -> int:
    email = normalize_email(email)
    error = validate(email, password)
    if error:
        print(f"Từ chối: {error}", file=sys.stderr)
        return 2
    engine = create_engine(get_settings().database_url)
    try:
        async with create_session_factory(engine)() as session:
            exists = await session.scalar(select(User.id).where(func.lower(User.email) == email))
            if exists is not None:
                print("Từ chối: email đã tồn tại.", file=sys.stderr)
                return 3
            team = None
            if team_code:
                team = await session.scalar(select(Team).where(Team.code == team_code))
                if team is None:
                    print(f"Từ chối: không có bộ phận {team_code}.", file=sys.stderr)
                    return 4
            user = User(email=email, display_name=name, role=role, password_hash=hash_password(password))
            session.add(user)
            await session.flush()
            if team is not None:
                session.add(TeamMember(team_id=team.id, user_id=user.id))
            await session.commit()
    finally:
        await engine.dispose()
    print(f"Đã tạo tài khoản {email} (vai trò {role}).")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True, help="tên hiển thị")
    parser.add_argument("--role", choices=[r.value for r in UserRole], default=UserRole.USER.value)
    parser.add_argument("--team", help="mã bộ phận: HR_ONBOARDING, IT, VINSOC, FACILITIES")
    parser.add_argument("--generate-password", action="store_true", help="tự sinh mật khẩu mạnh và in ra một lần")
    args = parser.parse_args()
    if args.generate_password:
        password = secrets.token_urlsafe(12)
        print(f"Mật khẩu (chỉ hiện một lần): {password}")
    else:
        password = getpass.getpass("Mật khẩu: ")
        if password != getpass.getpass("Nhập lại mật khẩu: "):
            print("Từ chối: hai lần nhập không khớp.", file=sys.stderr)
            sys.exit(2)
    sys.exit(asyncio.run(_run(args.email, args.name, args.role, password, args.team)))


if __name__ == "__main__":
    main()
