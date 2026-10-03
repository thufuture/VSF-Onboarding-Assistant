"""Viga của nhân viên trên PostgreSQL thật: công cụ lộ trình, LLM định tuyến, đường thoát, hội thoại lưu DB, riêng tư.

Kế hoạch: plan-portal/ingest-tai-lieu-va-tao-task-bang-ai.md mục 6.2, 15, 17. LLM và embedding là bản giả có kịch bản
(`viga_fixtures.ScriptedLlm`), nên không tốn tiền và kiểm được chính xác cái gì đã đi tới LLM.
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from viga_fixtures import (  # noqa: F401  (fixture được pytest tìm theo tên trong module này)
    MakeMember,
    ScriptedLlm,
    app,
    client_for,
    employee_tasks,
    llm_holder,
    login,
    make_member,
    other_team,
    published_template,
    route_json,
    session_factory,
    team,
)

from src.infrastructure.ai.deepseek_adapter import ChatCompletionError
from src.model.audit_log import AuditLog
from src.model.chat_conversation import ChatConversation
from src.model.chat_message import ChatMessage
from src.model.content_gap import ContentGap
from src.model.employee_journey import EmployeeJourney
from src.services.ingest.embedding.modal_adapter import EmbeddingServiceError
from src.services.viga import conversations

pytestmark = pytest.mark.integration

ASK = "/api/v1/viga/ask"


async def ask(client: Any, question: str, conversation_id: int | None = None) -> Any:
    body: dict[str, Any] = {"question": question}
    if conversation_id is not None:
        body["conversation_id"] = conversation_id
    return await client.post(ASK, json=body)


async def test_shortcut_phrase_answers_from_the_journey_without_any_llm_call(
    app: FastAPI,
    llm_holder: Any,
    team: SimpleNamespace,
    make_member: MakeMember,
    published_template: SimpleNamespace,
) -> None:
    employee = await make_member("USER", team.id, "Trần Anh Thư")

    async with client_for(app) as client:
        await login(client, employee)
        tasks = await employee_tasks(client)
        response = await ask(client, "Hôm nay làm gì?")

    body = response.json()
    assert response.status_code == 200, response.text
    assert body["response_type"] == "DAY_PLAN"
    assert body["route"] == "SHORTCUT"
    assert body["message_key"] == "dayPlan"
    assert body["message_params"] == {"day": "Ngày 1", "ready": 1, "total": 3}
    assert {"type": "OPEN_TASK", "title": "Nhận laptop", "task_id": tasks["Nhận laptop"], "stage_id": None} in body[
        "suggested_actions"
    ]
    assert body["can_report_to_hr"] is False
    assert llm_holder.llm.calls == []  # lối tắt: 0 lời gọi LLM


async def test_next_step_and_progress_shortcuts(
    app: FastAPI, team: SimpleNamespace, make_member: MakeMember, published_template: SimpleNamespace
) -> None:
    employee = await make_member("USER", team.id)

    async with client_for(app) as client:
        await login(client, employee)
        next_step = (await ask(client, "Tiếp theo tôi làm gì?")).json()
        progress = (await ask(client, "tiến độ của tôi")).json()

    assert next_step["response_type"] == "NEXT_STEP"
    assert next_step["message_params"] == {"title": "Nhận laptop"}
    assert progress["response_type"] == "INFO"
    assert progress["message_params"] == {"done": 0, "total": 4, "percent": 0}


async def test_llm_picks_explain_lock_and_code_validates_the_task(
    app: FastAPI,
    llm_holder: Any,
    team: SimpleNamespace,
    make_member: MakeMember,
    published_template: SimpleNamespace,
) -> None:
    employee = await make_member("USER", team.id)
    llm_holder.llm = ScriptedLlm()

    async with client_for(app) as client:
        await login(client, employee)
        tasks = await employee_tasks(client)
        avatar_id = tasks["Ảnh đại diện, chữ ký email"]
        llm_holder.llm.route = route_json("explain_lock", task_id=avatar_id)
        locked = (await ask(client, "Sao tôi chưa làm được task ảnh đại diện?")).json()
        # LLM bịa mã việc (hoặc của người khác): code chặn, không lộ gì.
        llm_holder.llm.route = route_json("explain_lock", task_id=99999999)
        foreign = (await ask(client, "việc số 99999999 sao bị khóa")).json()

    assert locked["response_type"] == "PREREQUISITE_REQUIRED"
    assert locked["route"] == "LLM"
    assert locked["message_params"] == {"title": "Ảnh đại diện, chữ ký email", "blocker": "Đăng nhập Outlook"}
    assert [b["title"] for b in locked["blocking_tasks"]] == ["Đăng nhập Outlook"]
    assert foreign["response_type"] == "NOT_IN_JOURNEY"
    assert foreign["blocking_tasks"] == [] and foreign["suggested_actions"] == []
    assert llm_holder.llm.kinds() == ["route", "route"]  # chỉ định tuyến; công cụ trả lời bằng dữ liệu, không thêm LLM


async def test_router_prompt_contains_task_names_but_no_personal_data(
    app: FastAPI,
    llm_holder: Any,
    team: SimpleNamespace,
    make_member: MakeMember,
    published_template: SimpleNamespace,
) -> None:
    employee = await make_member("USER", team.id, "Nguyễn Văn Bí Mật")
    llm_holder.llm = ScriptedLlm(route=route_json("get_progress"))

    async with client_for(app) as client:
        await login(client, employee)
        await ask(client, "mình đã xong bao nhiêu việc rồi nhỉ, cho mình xem tổng quan")

    prompt = llm_holder.llm.prompts("route")[0]
    assert "Nhận laptop" in prompt and "READY" in prompt
    assert employee.email not in prompt
    assert "Bí Mật" not in prompt  # tên nhân viên không đi ra dịch vụ LLM bên ngoài (quyết định 3)
    assert "Phòng nhân sự thử" not in prompt  # tên phòng ban cũng không


async def test_task_resolution_uses_last_opened_then_states_its_assumption(
    app: FastAPI,
    llm_holder: Any,
    team: SimpleNamespace,
    make_member: MakeMember,
    published_template: SimpleNamespace,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    employee = await make_member("USER", team.id)
    llm_holder.llm = ScriptedLlm(route=route_json("explain_lock", task_id=None))

    async with client_for(app) as client:
        await login(client, employee)
        tasks = await employee_tasks(client)
        # Chưa mở việc nào: Viga suy ra việc làm được ngay đầu tiên và NÓI RÕ giả định.
        assumed = (await ask(client, "task này sao chưa làm được")).json()
        # Mở trang một việc: backend ghi "việc vừa mở", lần sau không cần giả định.
        opened = await client.post(f"/api/v1/portal/me/tasks/{tasks['Ảnh đại diện, chữ ký email']}/opened")
        known = (await ask(client, "task này sao chưa làm được")).json()

    assert assumed["assumed_task_title"] == "Nhận laptop"
    assert assumed["message_key"] == "taskReady"
    assert opened.status_code == 204
    assert known["assumed_task_title"] is None
    assert known["response_type"] == "PREREQUISITE_REQUIRED"
    assert known["message_params"]["title"] == "Ảnh đại diện, chữ ký email"

    # Quá 30 phút thì việc vừa mở hết hiệu lực.
    async with session_factory() as session:
        await session.execute(update(EmployeeJourney).values(last_opened_at=datetime.now(UTC) - timedelta(minutes=31)))
        await session.commit()
    async with client_for(app) as client:
        await login(client, employee)
        stale = (await ask(client, "task này sao chưa làm được")).json()
    assert stale["assumed_task_title"] == "Nhận laptop"


async def test_cannot_mark_someone_elses_task_as_opened(
    app: FastAPI, team: SimpleNamespace, make_member: MakeMember, published_template: SimpleNamespace
) -> None:
    owner = await make_member("USER", team.id)
    intruder = await make_member("USER", team.id)

    async with client_for(app) as client:
        await login(client, owner)
        tasks = await employee_tasks(client)
    async with client_for(app) as client:
        await login(client, intruder)
        response = await client.post(f"/api/v1/portal/me/tasks/{tasks['Nhận laptop']}/opened")

    assert response.status_code == 404


async def test_ambiguity_asks_one_question_with_choices(
    app: FastAPI,
    llm_holder: Any,
    team: SimpleNamespace,
    make_member: MakeMember,
    published_template: SimpleNamespace,
) -> None:
    employee = await make_member("USER", team.id)
    llm_holder.llm = ScriptedLlm(route=route_json("explain_lock", clarify="Bạn đang nói về việc nào?", confidence=0.4))

    async with client_for(app) as client:
        await login(client, employee)
        body = (await ask(client, "cái này sao ấy nhỉ")).json()

    assert body["response_type"] == "CLARIFY"
    assert body["message"] == "Bạn đang nói về việc nào?"
    assert body["suggested_actions"], "phải kèm lựa chọn để bấm"
    assert body["can_report_to_hr"] is False  # CLARIFY không gợi ý ticket


async def test_personal_info_question_exits_without_llm_and_offers_hr(
    app: FastAPI, llm_holder: Any, team: SimpleNamespace, make_member: MakeMember, published_template: SimpleNamespace
) -> None:
    employee = await make_member("USER", team.id)

    async with client_for(app) as client:
        await login(client, employee)
        body = (await ask(client, "Mentor của mình là ai?")).json()

    assert body["response_type"] == "OUT_OF_SCOPE"
    assert body["route"] == "GUARD"
    assert body["can_report_to_hr"] is True
    assert llm_holder.llm.calls == []


async def test_small_talk_gets_a_polite_info_reply_without_ticket_suggestion(
    app: FastAPI, llm_holder: Any, team: SimpleNamespace, make_member: MakeMember, published_template: SimpleNamespace
) -> None:
    employee = await make_member("USER", team.id)
    llm_holder.llm = ScriptedLlm(route=route_json("none"))

    async with client_for(app) as client:
        await login(client, employee)
        body = (await ask(client, "xin chào Viga")).json()

    assert body["response_type"] == "INFO"
    assert body["message_key"] == "smalltalk"
    assert body["can_report_to_hr"] is False


async def test_router_failure_falls_back_to_documents_then_no_basis_with_gap_logged(
    app: FastAPI,
    llm_holder: Any,
    team: SimpleNamespace,
    make_member: MakeMember,
    published_template: SimpleNamespace,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    employee = await make_member("USER", team.id)
    question = f"Quy định gửi xe máy ở tầng hầm là gì {uuid4().hex[:6]}?"
    llm_holder.llm = ScriptedLlm(route=ChatCompletionError("lỗi mạng khi gọi LLM"))

    async with client_for(app) as client:
        await login(client, employee)
        body = (await ask(client, question)).json()

    assert body["response_type"] == "NO_BASIS"
    assert body["route"] == "FALLBACK"  # định tuyến lỗi -> lùi về hỏi đáp tài liệu (17.4)
    assert body["can_report_to_hr"] is True
    async with session_factory() as session:
        gaps = (await session.scalars(select(ContentGap).where(ContentGap.asked_by_user_id == employee.id))).all()
    assert [g.question_text for g in gaps] == [question]  # ghi cho HR bổ sung tài liệu


async def test_low_confidence_route_falls_back_to_documents(
    app: FastAPI, llm_holder: Any, team: SimpleNamespace, make_member: MakeMember, published_template: SimpleNamespace
) -> None:
    employee = await make_member("USER", team.id)
    llm_holder.llm = ScriptedLlm(route=route_json("get_progress", confidence=0.2))

    async with client_for(app) as client:
        await login(client, employee)
        body = (await ask(client, f"Điều kiện hưởng bảo hiểm sức khỏe {uuid4().hex[:6]}")).json()

    assert body["route"] == "FALLBACK"
    assert body["response_type"] == "NO_BASIS"


async def test_documents_failure_is_an_error_exit_not_a_500(
    app: FastAPI, llm_holder: Any, team: SimpleNamespace, make_member: MakeMember, published_template: SimpleNamespace
) -> None:
    employee = await make_member("USER", team.id)
    llm_holder.llm = ScriptedLlm(
        route=route_json("search_documents"), rewrite=ChatCompletionError("LLM không phản hồi")
    )

    async with client_for(app) as client:
        await login(client, employee)
        response = await ask(client, "Nghỉ phép năm được bao nhiêu ngày?")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["response_type"] == "ERROR"
    assert body["message_key"] == "assistantUnavailable"
    assert body["can_report_to_hr"] is True


async def test_missing_llm_key_still_serves_shortcuts_and_reports_error_for_documents(
    app: FastAPI, llm_holder: Any, team: SimpleNamespace, make_member: MakeMember, published_template: SimpleNamespace
) -> None:
    employee = await make_member("USER", team.id)
    llm_holder.llm = None  # chưa cấu hình khóa LLM

    async with client_for(app) as client:
        await login(client, employee)
        shortcut = (await ask(client, "Hôm nay làm gì?")).json()
        documents = (await ask(client, "Nghỉ phép năm được bao nhiêu ngày?")).json()

    assert shortcut["response_type"] == "DAY_PLAN"
    assert documents["response_type"] == "ERROR"


async def test_embedding_failure_is_an_error_exit(
    app: FastAPI, llm_holder: Any, team: SimpleNamespace, make_member: MakeMember, published_template: SimpleNamespace
) -> None:
    from src.api.dependencies import get_embedding_port

    class BrokenEmbedding:
        model_version = "x"
        dimension = 1024

        async def embed(self, texts: list[str]) -> list[list[float]]:
            raise EmbeddingServiceError("embedding không phản hồi")

    app.dependency_overrides[get_embedding_port] = lambda: BrokenEmbedding()
    employee = await make_member("USER", team.id)
    llm_holder.llm = ScriptedLlm(route=route_json("search_documents"))

    async with client_for(app) as client:
        await login(client, employee)
        body = (await ask(client, "Nghỉ phép năm được bao nhiêu ngày?")).json()

    assert body["response_type"] == "ERROR"


async def test_document_answer_has_a_validated_source_and_history_only_feeds_the_rewrite_step(
    app: FastAPI,
    llm_holder: Any,
    team: SimpleNamespace,
    make_member: MakeMember,
    published_template: SimpleNamespace,
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
) -> None:
    from src.model.document import Document
    from src.model.document_category import DocumentCategory
    from src.model.document_chunk import DocumentChunk
    from src.model.document_section import DocumentSection
    from src.model.document_version import DocumentVersion
    from src.model.enums import Confidentiality, ContentKind
    from src.services.ingest.embedding.fake_adapter import FakeEmbeddingAdapter
    from src.services.ingest.ingest_service import ingest_document, today_in
    from src.services.ingest.storage import LocalStorageAdapter

    hr = await make_member("HR", team.id)
    employee = await make_member("USER", team.id)
    slug = f"viga-test-{uuid4().hex[:8]}"
    key = f"viga-{uuid4().hex[:8]}"
    quote = "Nhân viên chính thức được nghỉ phép năm 12 ngày mỗi năm."
    path = tmp_path / "nghi-phep.md"
    path.write_text(
        f"# Nghỉ phép năm\n\n{quote} Ngày phép tính theo năm dương lịch và được chốt đầu năm sau. " * 6,
        encoding="utf-8",
    )
    async with session_factory() as session:
        session.add(DocumentCategory(slug=slug, name="Danh mục Viga thử"))
        await session.commit()
        await ingest_document(
            session,
            file_path=path,
            category_slug=slug,
            owner_email=hr.email,
            title="Quy định nghỉ phép thử",
            source_key=key,
            version_label="1.0",
            effective_from=today_in(),
            content_kind=ContentKind.GENERAL.value,
            confidentiality=Confidentiality.INTERNAL.value,
            embedding=FakeEmbeddingAdapter(),
            storage=LocalStorageAdapter(str(tmp_path)),
        )

    def answer(user_prompt: str) -> str:
        chunk = int(user_prompt.split("chunk_id=")[1].split(" ")[0].split("]")[0].split("—")[0])
        question = user_prompt.split('<question id="1">')[1].split("</question>")[0]
        return json.dumps(
            {
                "claims": [
                    {
                        "question": question,
                        "response_type": "ANSWER",
                        "text": "Nhân viên chính thức được nghỉ 12 ngày phép năm.",
                        "quote": quote,
                        "chunk_id": chunk,
                    }
                ]
            },
            ensure_ascii=False,
        )

    llm_holder.llm = ScriptedLlm(route=route_json("search_documents"), answer=answer)
    try:
        async with client_for(app) as client:
            await login(client, employee)
            first = (await ask(client, "Nghỉ phép năm được bao nhiêu ngày?")).json()
            second = (await ask(client, "còn nhân viên thử việc thì sao?", first["conversation_id"])).json()

        assert first["response_type"] == "ANSWER"
        assert first["claims"][0]["source"]["document_title"] == "Quy định nghỉ phép thử"
        assert first["claims"][0]["quote"] == quote
        assert first["can_report_to_hr"] is False
        # Lịch sử CHỈ đi vào bước viết lại câu hỏi (để hiểu "còn thử việc thì sao?"), không vào định tuyến hay trả lời.
        rewrite_prompts = llm_holder.llm.prompts("rewrite")
        assert "<history>" not in rewrite_prompts[0]
        assert "<history>" in rewrite_prompts[1] and "Nghỉ phép năm được bao nhiêu ngày?" in rewrite_prompts[1]
        assert all("<history>" not in prompt for prompt in llm_holder.llm.prompts("answer"))
        assert second["conversation_id"] == first["conversation_id"]
        assert second["new_conversation"] is False
    finally:
        async with session_factory() as session:
            doc = await session.scalar(select(Document).where(Document.source_key == key))
            if doc is not None:
                version_ids = list(
                    (
                        await session.scalars(select(DocumentVersion.id).where(DocumentVersion.document_id == doc.id))
                    ).all()
                )
                await session.execute(delete(DocumentChunk).where(DocumentChunk.version_id.in_(version_ids)))
                await session.execute(delete(DocumentSection).where(DocumentSection.version_id.in_(version_ids)))
                await session.execute(delete(DocumentVersion).where(DocumentVersion.id.in_(version_ids)))
                await session.execute(delete(Document).where(Document.id == doc.id))
            await session.execute(delete(DocumentCategory).where(DocumentCategory.slug == slug))
            await session.execute(delete(AuditLog).where(AuditLog.actor_id == hr.id))
            await session.commit()


async def test_conversations_are_stored_listed_reopened_renamed_and_deleted(
    app: FastAPI,
    team: SimpleNamespace,
    make_member: MakeMember,
    published_template: SimpleNamespace,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    employee = await make_member("USER", team.id)

    async with client_for(app) as client:
        await login(client, employee)
        first = (await ask(client, "Hôm nay làm gì?")).json()
        await ask(client, "Tiếp theo tôi làm gì?", first["conversation_id"])
        other = (await ask(client, "tiến độ của tôi")).json()

        listing = (await client.get("/api/v1/viga/conversations")).json()
        assert [c["id"] for c in listing] == [other["conversation_id"], first["conversation_id"]]  # mới nhất trước
        assert listing[1]["title"] == "Hôm nay làm gì?"  # tiêu đề lấy từ câu hỏi đầu

        detail = (await client.get(f"/api/v1/viga/conversations/{first['conversation_id']}")).json()
        assert [m["role"] for m in detail["messages"]] == ["USER", "ASSISTANT", "USER", "ASSISTANT"]
        reopened = detail["messages"][1]
        assert reopened["response_type"] == "DAY_PLAN"
        assert reopened["payload"]["message_key"] == "dayPlan"  # mở lại hiện đúng như lúc đã hỏi
        assert reopened["payload"]["actions"][0]["type"] in {"OPEN_DAY", "OPEN_TASK"}

        renamed = await client.patch(
            f"/api/v1/viga/conversations/{first['conversation_id']}", json={"title": "Việc ngày đầu"}
        )
        assert renamed.json()["title"] == "Việc ngày đầu"

        assert (await client.delete(f"/api/v1/viga/conversations/{first['conversation_id']}")).status_code == 204
        after = (await client.get("/api/v1/viga/conversations")).json()
        assert [c["id"] for c in after] == [other["conversation_id"]]
        assert (await client.get(f"/api/v1/viga/conversations/{first['conversation_id']}")).status_code == 404

    async with session_factory() as session:
        orphans = (
            await session.scalars(select(ChatMessage).where(ChatMessage.conversation_id == first["conversation_id"]))
        ).all()
    assert orphans == []  # xóa cuộc trò chuyện xóa luôn tin nhắn


async def test_conversations_are_private_to_their_owner(
    app: FastAPI, team: SimpleNamespace, make_member: MakeMember, published_template: SimpleNamespace
) -> None:
    owner = await make_member("USER", team.id)
    other = await make_member("USER", team.id)
    hr = await make_member("HR", team.id)

    async with client_for(app) as client:
        await login(client, owner)
        conversation_id = (await ask(client, "Hôm nay làm gì?")).json()["conversation_id"]

    for outsider in (other, hr):
        async with client_for(app) as client:
            await login(client, outsider)
            assert (await client.get(f"/api/v1/viga/conversations/{conversation_id}")).status_code == 404
            assert (await client.get("/api/v1/viga/conversations")).json() == []
            assert (await ask(client, "tiếp theo làm gì", conversation_id)).status_code == 404
            assert (await client.delete(f"/api/v1/viga/conversations/{conversation_id}")).status_code == 404


async def test_expired_conversations_are_purged_after_the_retention_period(
    app: FastAPI,
    team: SimpleNamespace,
    make_member: MakeMember,
    published_template: SimpleNamespace,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    employee = await make_member("USER", team.id)

    async with client_for(app) as client:
        await login(client, employee)
        old = (await ask(client, "Hôm nay làm gì?")).json()["conversation_id"]
        recent = (await ask(client, "tiến độ của tôi")).json()["conversation_id"]

    async with session_factory() as session:
        await session.execute(
            update(ChatConversation)
            .where(ChatConversation.id == old)
            .values(updated_at=datetime.now(UTC) - timedelta(days=91))
        )
        await session.commit()
        deleted = await conversations.purge_expired(session, retention_days=90)
        left = (await session.scalars(select(ChatConversation.id).where(ChatConversation.user_id == employee.id))).all()

    assert deleted >= 1
    assert list(left) == [recent]


async def test_rate_limit_applies_to_viga_like_chat(
    app: FastAPI, team: SimpleNamespace, make_member: MakeMember, published_template: SimpleNamespace
) -> None:
    from src.services.chat.chat_throttle import ChatThrottle

    app.state.chat_throttle = ChatThrottle(2, 60)
    employee = await make_member("USER", team.id)

    async with client_for(app) as client:
        await login(client, employee)
        await ask(client, "Hôm nay làm gì?")
        await ask(client, "Hôm nay làm gì?")
        blocked = await ask(client, "Hôm nay làm gì?")

    assert blocked.status_code == 429
    assert blocked.json()["code"] == "TOO_MANY_QUESTIONS"
    assert int(blocked.headers["retry-after"]) > 0


async def test_empty_question_is_rejected_and_nothing_is_stored(
    app: FastAPI, team: SimpleNamespace, make_member: MakeMember, published_template: SimpleNamespace
) -> None:
    employee = await make_member("USER", team.id)

    async with client_for(app) as client:
        await login(client, employee)
        response = await ask(client, "    ")
        listing = (await client.get("/api/v1/viga/conversations")).json()

    assert response.status_code == 422
    assert listing == []


async def test_viga_requires_login(app: FastAPI) -> None:
    async with client_for(app) as client:
        response = await ask(client, "Hôm nay làm gì?")

    assert response.status_code == 401
