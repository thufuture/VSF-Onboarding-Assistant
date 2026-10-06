"""Fixture dùng chung cho test Viga và ticket trên PostgreSQL thật: nhân viên, HR, lộ trình đã publish, LLM giả có kịch bản.

LLM giả phân biệt ba loại lời gọi theo system prompt (định tuyến, viết lại câu hỏi, sinh câu trả lời) và ghi lại để test kiểm
được cái gì đã đi tới LLM (ví dụ: không có email, có lịch sử ở bước viết lại, câu lối tắt không tốn lời gọi nào).
"""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.dependencies import get_embedding_port, get_optional_chat_completion_port
from src.config import Settings, get_settings
from src.infrastructure.persistence.engine import create_session_factory
from src.main import create_app
from src.model.audit_log import AuditLog
from src.model.content_gap import ContentGap
from src.model.employee_journey import EmployeeJourney
from src.model.employee_task import EmployeeTask
from src.model.enums import JourneyTemplateStatus, StageVersionStatus
from src.model.journey_stage import JourneyStage
from src.model.journey_template import JourneyTemplate
from src.model.stage_version import StageVersion
from src.model.task_dependency import TaskDependency
from src.model.task_template import TaskTemplate
from src.model.team import Team
from src.model.team_member import TeamMember
from src.model.ticket import Ticket
from src.model.user import User
from src.services.auth.login_throttle import LoginThrottle
from src.services.auth.passwords import hash_password
from src.services.ingest.embedding.fake_adapter import FakeEmbeddingAdapter

SECRET = "f3b1c9d2a7e84f6b95a0c3d1e7b28a4f6d0c9e5b1a3f7d2c"
PASSWORD = "ChangeMe!123"

MakeMember = Callable[..., Awaitable[SimpleNamespace]]
Responder = str | Callable[[str], str] | Exception | None


@dataclass
class ScriptedLlm:
    """LLM giả theo kịch bản. `route`/`answer`/`rewrite` là chuỗi JSON, hàm nhận user_prompt, hoặc một ngoại lệ để ném."""

    route: Responder = None
    answer: Responder = None
    rewrite: Responder = None
    calls: list[tuple[str, str, str]] = field(default_factory=list)  # (loại, system, user)

    def kinds(self) -> list[str]:
        return [kind for kind, _, _ in self.calls]

    def prompts(self, kind: str) -> list[str]:
        return [user for k, _, user in self.calls if k == kind]

    async def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        timeout_seconds: float | None = None,
        reasoning: bool = True,
        stream: bool = False,
        temperature: float | None = None,
    ) -> str:
        if "bộ định tuyến" in system_prompt:
            kind, script = "route", self.route
        elif "nhân sự mới" in system_prompt and "viết lại" in system_prompt:
            kind, script = "rewrite", self.rewrite
        else:
            kind, script = "answer", self.answer
        self.calls.append((kind, system_prompt, user_prompt))
        if isinstance(script, Exception):
            raise script
        if callable(script):
            return script(user_prompt)
        if isinstance(script, str):
            return script
        return self._default(kind, user_prompt)

    @staticmethod
    def _default(kind: str, user_prompt: str) -> str:
        if kind == "rewrite":
            match = re.search(r"<user_input>(.*?)</user_input>", user_prompt, flags=re.DOTALL)
            return json.dumps(
                {"standalone_questions": [match.group(1).strip() if match else user_prompt]}, ensure_ascii=False
            )
        if kind == "answer":
            questions = re.findall(r'<question id="\d+">(.*?)</question>', user_prompt, flags=re.DOTALL)
            claims = [{"question": q, "response_type": "NO_BASIS", "reason_code": "no_evidence"} for q in questions]
            return json.dumps({"claims": claims}, ensure_ascii=False)
        return json.dumps({"tool": "none", "args": {}, "confidence": 0.9, "clarify": None})


def route_json(tool: str, *, confidence: float = 0.9, clarify: str | None = None, **args: object) -> str:
    return json.dumps({"tool": tool, "args": args, "confidence": confidence, "clarify": clarify}, ensure_ascii=False)


class LlmHolder:
    llm: ScriptedLlm | None = None


@pytest.fixture
def llm_holder() -> LlmHolder:
    holder = LlmHolder()
    holder.llm = ScriptedLlm()
    return holder


@pytest.fixture
async def session_factory(migrated_database_url: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(migrated_database_url)
    try:
        yield create_session_factory(engine)
    finally:
        await engine.dispose()


@pytest.fixture
async def team(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[SimpleNamespace]:
    async with session_factory() as session:
        row = Team(code=f"team-{uuid4().hex[:8]}", name="Phòng nhân sự thử")
        session.add(row)
        await session.commit()
        result = SimpleNamespace(id=row.id)
    yield result
    async with session_factory() as session:
        await session.execute(delete(Team).where(Team.id == result.id))
        await session.commit()


@pytest.fixture
async def other_team(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[SimpleNamespace]:
    async with session_factory() as session:
        row = Team(code=f"team-{uuid4().hex[:8]}", name="Phòng khác")
        session.add(row)
        await session.commit()
        result = SimpleNamespace(id=row.id)
    yield result
    async with session_factory() as session:
        await session.execute(delete(Team).where(Team.id == result.id))
        await session.commit()


@pytest.fixture
async def make_member(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[MakeMember]:
    created: list[int] = []

    async def make(role: str, team_id: int, name: str = "Người thử") -> SimpleNamespace:
        email = f"viga-{uuid4().hex[:10]}@example.test"
        async with session_factory() as session:
            user = User(email=email, display_name=name, role=role, password_hash=hash_password(PASSWORD))
            session.add(user)
            await session.flush()
            session.add(TeamMember(team_id=team_id, user_id=user.id))
            await session.commit()
            created.append(user.id)
            return SimpleNamespace(email=email, password=PASSWORD, id=user.id, role=role, team_id=team_id)

    yield make
    if not created:
        return
    async with session_factory() as session:
        await session.execute(delete(Ticket).where(Ticket.created_by_user_id.in_(created)))
        await session.execute(delete(ContentGap).where(ContentGap.asked_by_user_id.in_(created)))
        journey_ids = list(
            (await session.scalars(select(EmployeeJourney.id).where(EmployeeJourney.user_id.in_(created)))).all()
        )
        if journey_ids:
            await session.execute(
                delete(EmployeeJourney)
                .where(EmployeeJourney.id.in_(journey_ids))
                .execution_options(synchronize_session=False)
            )
        await session.execute(delete(AuditLog).where(AuditLog.actor_id.in_(created)))
        await session.execute(delete(TeamMember).where(TeamMember.user_id.in_(created)))
        await session.execute(delete(User).where(User.id.in_(created)))
        await session.commit()


@pytest.fixture
async def published_template(
    session_factory: async_sessionmaker[AsyncSession], team: SimpleNamespace
) -> AsyncIterator[SimpleNamespace]:
    """Ngày 1: Nhận laptop (làm được ngay) -> Đăng nhập Outlook -> Ảnh đại diện (khóa); Ngày 2: đào tạo hội nhập."""
    async with session_factory() as session:
        creator = User(
            email=f"viga-creator-{uuid4().hex[:10]}@example.test",
            display_name="HR tạo lộ trình",
            role="HR",
            password_hash=hash_password(PASSWORD),
        )
        session.add(creator)
        await session.flush()
        template = JourneyTemplate(
            code=f"tpl-{uuid4().hex[:8]}",
            title="Lộ trình thử",
            status=JourneyTemplateStatus.PUBLISHED.value,
            team_id=team.id,
            created_by=creator.id,
        )
        session.add(template)
        await session.flush()
        day1 = JourneyStage(journey_template_id=template.id, title="Ngày 1", sort_order=1)
        day2 = JourneyStage(journey_template_id=template.id, title="Ngày 2", sort_order=2)
        session.add_all([day1, day2])
        await session.flush()
        version1 = StageVersion(journey_stage_id=day1.id, version_no=1, status=StageVersionStatus.APPLIED.value)
        version2 = StageVersion(journey_stage_id=day2.id, version_no=1, status=StageVersionStatus.APPLIED.value)
        session.add_all([version1, version2])
        await session.flush()
        laptop = TaskTemplate(
            journey_stage_id=day1.id,
            stage_version_id=version1.id,
            title="Nhận laptop",
            body_markdown="## Các bước\n1. Nhận laptop tại tầng 12",
            sort_order=1,
        )
        outlook = TaskTemplate(
            journey_stage_id=day1.id,
            stage_version_id=version1.id,
            title="Đăng nhập Outlook",
            body_markdown="Đăng nhập.",
            sort_order=2,
        )
        avatar = TaskTemplate(
            journey_stage_id=day1.id,
            stage_version_id=version1.id,
            title="Ảnh đại diện, chữ ký email",
            body_markdown="Đặt ảnh.",
            sort_order=3,
        )
        training = TaskTemplate(
            journey_stage_id=day2.id,
            stage_version_id=version2.id,
            title="Tham gia đào tạo hội nhập",
            body_markdown="Đến phòng đào tạo.",
            sort_order=1,
        )
        session.add_all([laptop, outlook, avatar, training])
        await session.flush()
        session.add_all(
            [
                TaskDependency(task_template_id=outlook.id, depends_on_task_template_id=laptop.id),
                TaskDependency(task_template_id=avatar.id, depends_on_task_template_id=outlook.id),
            ]
        )
        await session.commit()
        ids = SimpleNamespace(
            template_id=template.id,
            creator_id=creator.id,
            laptop=laptop.id,
            outlook=outlook.id,
            avatar=avatar.id,
            training=training.id,
        )
    yield ids
    async with session_factory() as session:
        journey_ids = list(
            (
                await session.scalars(
                    select(EmployeeJourney.id).where(EmployeeJourney.journey_template_id == ids.template_id)
                )
            ).all()
        )
        if journey_ids:
            await session.execute(delete(EmployeeTask).where(EmployeeTask.employee_journey_id.in_(journey_ids)))
            await session.execute(delete(EmployeeJourney).where(EmployeeJourney.id.in_(journey_ids)))
        task_ids = [ids.laptop, ids.outlook, ids.avatar, ids.training]
        await session.execute(delete(TaskDependency).where(TaskDependency.task_template_id.in_(task_ids)))
        await session.execute(delete(TaskTemplate).where(TaskTemplate.id.in_(task_ids)))
        await session.execute(delete(JourneyStage).where(JourneyStage.journey_template_id == ids.template_id))
        await session.execute(delete(JourneyTemplate).where(JourneyTemplate.id == ids.template_id))
        await session.execute(delete(AuditLog).where(AuditLog.actor_id == ids.creator_id))
        await session.execute(delete(User).where(User.id == ids.creator_id))
        await session.commit()


@pytest.fixture
def app(session_factory: async_sessionmaker[AsyncSession], llm_holder: LlmHolder) -> FastAPI:
    settings = Settings(_env_file=None, session_secret=SECRET, login_max_failures=3, login_window_seconds=900)
    application = create_app()
    application.state.session_factory = session_factory
    application.state.login_throttle = LoginThrottle(3, 900)
    application.dependency_overrides[get_settings] = lambda: settings
    application.dependency_overrides[get_embedding_port] = lambda: FakeEmbeddingAdapter()
    application.dependency_overrides[get_optional_chat_completion_port] = lambda: llm_holder.llm
    return application


def client_for(app: FastAPI) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app, client=("10.0.0.1", 5000))
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def login(client: httpx.AsyncClient, user: SimpleNamespace) -> httpx.Response:
    response = await client.post("/api/v1/auth/login", json={"email": user.email, "password": user.password})
    assert response.status_code == 200, response.text
    return response


async def employee_tasks(client: httpx.AsyncClient) -> dict[str, int]:
    """Mã việc của chính nhân viên đang đăng nhập, theo tên việc (gọi `/me/journey` tạo lộ trình lần đầu)."""
    created = await client.post("/api/v1/portal/me/journey")
    assert created.status_code in (200, 201), created.text
    response = await client.get("/api/v1/portal/me/journey")
    assert response.status_code == 200, response.text
    return {task["title"]: task["id"] for task in response.json()["tasks"]}
