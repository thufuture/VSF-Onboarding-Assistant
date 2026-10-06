"""Đánh giá 👍/👎 cho câu trả lời Viga, danh sách "chưa hài lòng" ẩn danh cho HR, và đường thoát PARTIAL.

Quy tắc: mỗi câu trả lời một đánh giá (bấm lại để đổi), chỉ chủ hội thoại đánh giá được, HR chỉ thấy theo phòng ban và không thấy
tên người đánh giá.
"""

import json
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from viga_fixtures import (  # noqa: F401  (fixture được pytest tìm theo tên trong module này)
    MakeMember,
    ScriptedLlm,
    app,
    client_for,
    llm_holder,
    login,
    make_member,
    other_team,
    published_template,
    route_json,
    session_factory,
    team,
)

from src.model.content_gap import ContentGap

pytestmark = pytest.mark.integration


async def _ask(client: Any, question: str) -> dict[str, Any]:
    response = await client.post("/api/v1/viga/ask", json={"question": question})
    assert response.status_code == 200, response.text
    return dict(response.json())


async def test_rating_can_be_set_changed_and_cleared_and_survives_reopening(
    app: FastAPI,
    llm_holder: Any,
    team: SimpleNamespace,
    make_member: MakeMember,
    published_template: SimpleNamespace,
) -> None:
    employee = await make_member("USER", team.id)
    llm_holder.llm = ScriptedLlm(route=route_json("search_documents"))

    async with client_for(app) as client:
        await login(client, employee)
        answer = await _ask(client, f"Câu hỏi thử {uuid4().hex[:6]}")
        url = f"/api/v1/viga/messages/{answer['message_id']}/feedback"

        up = await client.put(url, json={"rating": "UP"})
        assert up.status_code == 200 and up.json()["rating"] == "UP"

        down = await client.put(url, json={"rating": "DOWN", "reason": "WRONG", "comment": "  Sai   chỗ nhận máy "})
        assert down.json() == {
            "message_id": answer["message_id"],
            "rating": "DOWN",
            "reason": "WRONG",
            "comment": "Sai chỗ nhận máy",
        }

        detail = (await client.get(f"/api/v1/viga/conversations/{answer['conversation_id']}")).json()
        rated = [m for m in detail["messages"] if m["id"] == answer["message_id"]][0]
        assert rated["feedback"] == {"rating": "DOWN", "reason": "WRONG"}
        assert [m["feedback"] for m in detail["messages"] if m["role"] == "USER"] == [None]

        assert (await client.delete(url)).status_code == 204
        detail = (await client.get(f"/api/v1/viga/conversations/{answer['conversation_id']}")).json()
        assert all(m["feedback"] is None for m in detail["messages"])


async def test_only_the_owner_can_rate_and_only_assistant_messages(
    app: FastAPI,
    llm_holder: Any,
    team: SimpleNamespace,
    make_member: MakeMember,
    published_template: SimpleNamespace,
) -> None:
    owner = await make_member("USER", team.id)
    stranger = await make_member("USER", team.id)
    llm_holder.llm = ScriptedLlm(route=route_json("search_documents"))

    async with client_for(app) as client:
        await login(client, owner)
        answer = await _ask(client, f"Câu hỏi riêng {uuid4().hex[:6]}")
        detail = (await client.get(f"/api/v1/viga/conversations/{answer['conversation_id']}")).json()
        user_message = [m for m in detail["messages"] if m["role"] == "USER"][0]
        own_question = await client.put(f"/api/v1/viga/messages/{user_message['id']}/feedback", json={"rating": "UP"})
        assert own_question.status_code == 404  # chỉ câu trả lời của Viga mới đánh giá được

    async with client_for(app) as client:
        await login(client, stranger)
        stolen = await client.put(f"/api/v1/viga/messages/{answer['message_id']}/feedback", json={"rating": "DOWN"})
        assert stolen.status_code == 404  # không lộ sự tồn tại của hội thoại người khác
        assert (await client.put("/api/v1/viga/messages/999999999/feedback", json={"rating": "UP"})).status_code == 404
        bad_reason = await client.put(
            f"/api/v1/viga/messages/{answer['message_id']}/feedback", json={"rating": "DOWN", "reason": "TỆ"}
        )
        assert bad_reason.status_code == 422


async def test_hr_sees_dissatisfied_questions_anonymously_scoped_to_the_team(
    app: FastAPI,
    llm_holder: Any,
    team: SimpleNamespace,
    other_team: SimpleNamespace,
    make_member: MakeMember,
    published_template: SimpleNamespace,
) -> None:
    first = await make_member("USER", team.id, "Trần Anh Thư")
    second = await make_member("USER", team.id, "Lê Văn B")
    far = await make_member("USER", other_team.id, "Người phòng khác")
    hr = await make_member("HR", team.id)
    far_hr = await make_member("HR", other_team.id)
    unique = uuid4().hex[:8]
    question = f"Gửi xe máy tầng hầm thế nào {unique}?"
    llm_holder.llm = ScriptedLlm(route=route_json("search_documents"))

    for employee, text, rating, reason in (
        (first, question, "DOWN", "MISSING"),
        (second, question.lower(), "DOWN", "UNCLEAR"),
        (far, f"Câu của phòng khác {unique}", "DOWN", None),
    ):
        async with client_for(app) as client:
            await login(client, employee)
            answer = await _ask(client, text)
            body: dict[str, Any] = {"rating": rating}
            if reason:
                body["reason"] = reason
            assert (
                await client.put(f"/api/v1/viga/messages/{answer['message_id']}/feedback", json=body)
            ).status_code == 200

    async with client_for(app) as client:
        await login(client, hr)
        groups = (await client.get("/api/v1/portal/viga-feedback")).json()
        mine = [g for g in groups if unique in g["question_text"]]
        assert len(mine) == 1 and mine[0]["occurrences"] == 2  # câu giống nhau gom lại
        assert sorted(mine[0]["reasons"]) == ["MISSING", "UNCLEAR"]
        assert "Trần" not in str(groups) and "Lê Văn" not in str(groups)  # ẩn danh
        assert not any("phòng khác" in g["question_text"] for g in groups)

        summary = (await client.get("/api/v1/portal/viga-feedback/summary")).json()
        assert summary["down"] >= 2 and summary["open_down"] >= 2

        assert (await client.post(f"/api/v1/portal/viga-feedback/{mine[0]['id']}/resolve")).status_code == 204
        after = (await client.get("/api/v1/portal/viga-feedback")).json()
        assert not any(unique in g["question_text"] for g in after)
        with_resolved = (await client.get("/api/v1/portal/viga-feedback?include_resolved=true")).json()
        assert any(unique in g["question_text"] and g["resolved"] for g in with_resolved)

    async with client_for(app) as client:
        await login(client, far_hr)
        assert (await client.post(f"/api/v1/portal/viga-feedback/{mine[0]['id']}/resolve")).status_code == 404

    async with client_for(app) as client:
        await login(client, first)
        assert (await client.get("/api/v1/portal/viga-feedback")).status_code == 403  # nhân viên không xem được


async def test_changing_a_rating_back_to_up_removes_it_from_the_hr_list(
    app: FastAPI,
    llm_holder: Any,
    team: SimpleNamespace,
    make_member: MakeMember,
    published_template: SimpleNamespace,
) -> None:
    employee = await make_member("USER", team.id)
    hr = await make_member("HR", team.id)
    unique = uuid4().hex[:8]
    llm_holder.llm = ScriptedLlm(route=route_json("search_documents"))

    async with client_for(app) as client:
        await login(client, employee)
        answer = await _ask(client, f"Câu đổi ý {unique}")
        url = f"/api/v1/viga/messages/{answer['message_id']}/feedback"
        await client.put(url, json={"rating": "DOWN"})
        await client.put(url, json={"rating": "UP"})

    async with client_for(app) as client:
        await login(client, hr)
        groups = (await client.get("/api/v1/portal/viga-feedback")).json()
        assert not any(unique in g["question_text"] for g in groups)


async def test_partly_answered_question_lists_what_is_missing_and_logs_a_partial_gap(
    app: FastAPI,
    llm_holder: Any,
    team: SimpleNamespace,
    make_member: MakeMember,
    published_template: SimpleNamespace,
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Any,
) -> None:
    """Trả lời được ý 1, ý 2 tài liệu chưa quy định: ANSWER kèm `unanswered`, gap loại PARTIAL (không phải NO_BASIS)."""
    from src.model.audit_log import AuditLog
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
    slug = f"viga-partial-{uuid4().hex[:8]}"
    key = f"viga-partial-{uuid4().hex[:8]}"
    quote = "Nhân viên mới nhận laptop tại tầng 12 của tòa nhà."
    path = tmp_path / "laptop.md"
    path.write_text(f"# Nhận laptop\n\n{quote} Mang theo thẻ nhân viên khi đến nhận máy. " * 6, encoding="utf-8")
    async with session_factory() as session:
        session.add(DocumentCategory(slug=slug, name="Danh mục thử PARTIAL"))
        await session.commit()
        await ingest_document(
            session,
            file_path=path,
            category_slug=slug,
            owner_email=hr.email,
            title="Hướng dẫn nhận máy thử",
            source_key=key,
            version_label="1.0",
            effective_from=today_in(),
            content_kind=ContentKind.GENERAL.value,
            confidentiality=Confidentiality.INTERNAL.value,
            embedding=FakeEmbeddingAdapter(),
            storage=LocalStorageAdapter(str(tmp_path)),
        )

    def rewrite(user_prompt: str) -> str:
        return json.dumps(
            {"standalone_questions": ["Nhận laptop ở đâu?", "Có được đổi máy khác không?"]}, ensure_ascii=False
        )

    def answer(user_prompt: str) -> str:
        chunk = int(user_prompt.split("chunk_id=")[1].split(" ")[0].split("]")[0].split("—")[0])
        return json.dumps(
            {
                "claims": [
                    {
                        "question": "Nhận laptop ở đâu?",
                        "response_type": "ANSWER",
                        "text": "Nhận laptop tại tầng 12.",
                        "quote": quote,
                        "chunk_id": chunk,
                    },
                    {
                        "question": "Có được đổi máy khác không?",
                        "response_type": "NO_BASIS",
                        "reason_code": "no_evidence",
                    },
                ]
            },
            ensure_ascii=False,
        )

    try:
        llm_holder.llm = ScriptedLlm(route=route_json("search_documents"), rewrite=rewrite, answer=answer)
        unique = uuid4().hex[:8]
        question = f"Nhận laptop ở đâu và có được đổi máy khác không {unique}?"

        async with client_for(app) as client:
            await login(client, employee)
            body = await _ask(client, question)

        assert body["response_type"] == "ANSWER"
        assert body["unanswered"] == ["Có được đổi máy khác không?"]
        assert body["can_report_to_hr"] is True
        async with session_factory() as session:
            gaps = (await session.scalars(select(ContentGap).where(ContentGap.question_text.contains(unique)))).all()
        assert [(g.kind, bool(g.answer_excerpt)) for g in gaps] == [("PARTIAL", True)]

        async with client_for(app) as client:
            await login(client, hr)
            listed = [
                g for g in (await client.get("/api/v1/portal/content-gaps")).json() if unique in g["question_text"]
            ]
        assert listed[0]["kind"] == "PARTIAL" and "tầng 12" in listed[0]["answer_excerpt"]

        # Kiểm lại sau khi bổ sung tài liệu: chưa trả lời được thì để mở, trả lời được thì tự đóng và ghi tài liệu đã bổ sung.
        gap_url = f"/api/v1/portal/content-gaps/{listed[0]['id']}/recheck"
        async with client_for(app) as client:
            await login(client, hr)
            llm_holder.llm = ScriptedLlm(route=route_json("search_documents"))  # câu trả lời mặc định: không có căn cứ
            miss = (await client.post(gap_url)).json()
            assert miss["answered"] is False and miss["closed"] == 0
            still_open = [
                g for g in (await client.get("/api/v1/portal/content-gaps")).json() if unique in g["question_text"]
            ]
            assert len(still_open) == 1

            llm_holder.llm = ScriptedLlm(rewrite=rewrite, answer=answer)
            hit = (await client.post(gap_url)).json()
            assert hit["answered"] is True and "tầng 12" in hit["message"] and hit["closed"] == 1
            assert hit["document_title"] == "Hướng dẫn nhận máy thử"
            closed = [
                g
                for g in (await client.get("/api/v1/portal/content-gaps?include_resolved=true")).json()
                if unique in g["question_text"]
            ]
            assert closed[0]["resolved"] and closed[0]["resolved_document_title"] == "Hướng dẫn nhận máy thử"
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


async def test_hr_can_supplement_a_gap_with_a_written_answer(
    app: FastAPI,
    llm_holder: Any,
    team: SimpleNamespace,
    other_team: SimpleNamespace,
    make_member: MakeMember,
    published_template: SimpleNamespace,
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Any,
) -> None:
    """HR viết đáp án ngay trên câu hỏi chưa trả lời được: vào tài liệu "Hỏi đáp bổ sung" của phòng ban và xếp việc kích hoạt."""
    from src.api.dependencies import get_storage_port
    from src.model.audit_log import AuditLog
    from src.model.document import Document
    from src.model.document_version import DocumentVersion
    from src.model.job import Job
    from src.services.ingest.storage import LocalStorageAdapter

    app.dependency_overrides[get_storage_port] = lambda: LocalStorageAdapter(str(tmp_path))
    employee = await make_member("USER", team.id)
    hr = await make_member("HR", team.id)
    far_hr = await make_member("HR", other_team.id)
    unique = uuid4().hex[:8]
    llm_holder.llm = ScriptedLlm(route=route_json("search_documents"))
    key = f"qa-supplement-team-{team.id}"

    try:
        async with client_for(app) as client:
            await login(client, employee)
            await _ask(client, f"Nhận phụ cấp gửi xe ở đâu {unique}?")
        async with client_for(app) as client:
            await login(client, hr)
            gap = [g for g in (await client.get("/api/v1/portal/content-gaps")).json() if unique in g["question_text"]][
                0
            ]
            url = f"/api/v1/portal/content-gaps/{gap['id']}/supplement"

            assert (await client.post(url, json={"answer": "ok"})).status_code == 422  # quá ngắn
            created = await client.post(
                url, json={"answer": "Nhận phụ cấp gửi xe tại phòng Hành chính tầng 3.", "contact": "Phòng Hành chính"}
            )
            assert created.status_code == 202, created.text
            body = created.json()
            assert body["version_label"] == "Bổ sung 1" and body["job_id"] > 0

        async with client_for(app) as client:
            await login(client, far_hr)
            assert (await client.post(url, json={"answer": "Câu trả lời của phòng khác."})).status_code == 404

        async with session_factory() as session:
            document = await session.scalar(select(Document).where(Document.source_key == key))
            assert document is not None and document.title == "Hỏi đáp bổ sung"
            version = await session.get(DocumentVersion, body["document_version_id"])
            assert version is not None
            assert f"## Nhận phụ cấp gửi xe ở đâu {unique}?" in version.markdown
            assert "phòng Hành chính tầng 3" in version.markdown and "Đầu mối: Phòng Hành chính" in version.markdown
            assert await session.get(Job, body["job_id"]) is not None
    finally:
        app.dependency_overrides.pop(get_storage_port, None)
        async with session_factory() as session:
            document = await session.scalar(select(Document).where(Document.source_key == key))
            if document is not None:
                version_ids = list(
                    (
                        await session.scalars(
                            select(DocumentVersion.id).where(DocumentVersion.document_id == document.id)
                        )
                    ).all()
                )
                await session.execute(delete(Job).where(Job.document_version_id.in_(version_ids)))
                await session.execute(delete(DocumentVersion).where(DocumentVersion.id.in_(version_ids)))
                await session.execute(delete(Document).where(Document.id == document.id))
            await session.execute(delete(AuditLog).where(AuditLog.actor_id.in_([hr.id, far_hr.id])))
            await session.commit()


async def test_answer_with_a_wrong_quote_is_retried_once_and_not_logged_as_a_gap_when_recovered(
    app: FastAPI,
    llm_holder: Any,
    team: SimpleNamespace,
    make_member: MakeMember,
    published_template: SimpleNamespace,
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Any,
) -> None:
    """Mô hình đôi khi trích sai một chữ: thử lại đúng một lần. Lần hai đúng thì trả lời bình thường; vẫn sai thì mới NO_BASIS."""
    from src.model.audit_log import AuditLog
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
    slug = f"viga-retry-{uuid4().hex[:8]}"
    key = f"viga-retry-{uuid4().hex[:8]}"
    quote = "Nhân viên mới nhận laptop tại tầng 12 của tòa nhà."
    path = tmp_path / "laptop.md"
    path.write_text(f"# Nhận laptop\n\n* {quote}\n* Mang theo thẻ nhân viên khi đến nhận máy. " * 6, encoding="utf-8")
    async with session_factory() as session:
        session.add(DocumentCategory(slug=slug, name="Danh mục thử retry"))
        await session.commit()
        await ingest_document(
            session,
            file_path=path,
            category_slug=slug,
            owner_email=hr.email,
            title="Hướng dẫn nhận máy retry",
            source_key=key,
            version_label="1.0",
            effective_from=today_in(),
            content_kind=ContentKind.GENERAL.value,
            confidentiality=Confidentiality.INTERNAL.value,
            embedding=FakeEmbeddingAdapter(),
            storage=LocalStorageAdapter(str(tmp_path)),
        )

    state = {"calls": 0, "good_on": 2}

    def answer(user_prompt: str) -> str:
        state["calls"] += 1
        chunk = int(user_prompt.split("chunk_id=")[1].split(" ")[0].split("]")[0].split("—")[0])
        question = user_prompt.split('<question id="1">')[1].split("</question>")[0]
        used = quote if state["calls"] >= state["good_on"] else "Nhân viên mới nhận laptop tại tầng 99 của tòa nhà."
        return json.dumps(
            {
                "claims": [
                    {
                        "question": question,
                        "response_type": "ANSWER",
                        "text": "Nhận laptop tại tầng 12.",
                        "quote": used,
                        "chunk_id": chunk,
                    }
                ]
            },
            ensure_ascii=False,
        )

    try:
        llm_holder.llm = ScriptedLlm(route=route_json("search_documents"), answer=answer)
        unique = uuid4().hex[:8]

        async with client_for(app) as client:
            await login(client, employee)
            recovered = await _ask(client, f"Nhận laptop ở đâu {unique}?")
        assert recovered["response_type"] == "ANSWER"
        assert recovered["claims"][0]["quote"].startswith("Nhân viên mới nhận laptop tại tầng 12")  # lần hai đúng chữ
        assert state["calls"] == 2

        state.update(calls=0, good_on=99)  # lần nào cũng sai: chỉ thử lại đúng một lần rồi dừng
        async with client_for(app) as client:
            await login(client, employee)
            failed = await _ask(client, f"Nhận máy ở tầng nào {unique}?")
        assert failed["response_type"] == "NO_BASIS"
        assert state["calls"] == 2
        async with session_factory() as session:
            gaps = (await session.scalars(select(ContentGap).where(ContentGap.question_text.contains(unique)))).all()
        assert [g.question_text for g in gaps] == [
            f"Nhận máy ở tầng nào {unique}?"
        ]  # câu đã hồi phục không bị ghi thiếu tài liệu
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


async def test_hr_can_supplement_and_recheck_a_disliked_question(
    app: FastAPI,
    llm_holder: Any,
    team: SimpleNamespace,
    other_team: SimpleNamespace,
    make_member: MakeMember,
    published_template: SimpleNamespace,
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Any,
) -> None:
    """Câu bị 👎 cũng bổ sung được tài liệu và kiểm tra lại như câu chưa trả lời được; HR phòng khác không đụng được."""
    from src.api.dependencies import get_storage_port
    from src.model.audit_log import AuditLog
    from src.model.document import Document
    from src.model.document_version import DocumentVersion
    from src.model.job import Job
    from src.services.ingest.storage import LocalStorageAdapter

    app.dependency_overrides[get_storage_port] = lambda: LocalStorageAdapter(str(tmp_path))
    employee = await make_member("USER", team.id)
    hr = await make_member("HR", team.id)
    far_hr = await make_member("HR", other_team.id)
    unique = uuid4().hex[:8]
    llm_holder.llm = ScriptedLlm(route=route_json("search_documents"))
    key = f"qa-supplement-team-{team.id}"

    try:
        async with client_for(app) as client:
            await login(client, employee)
            answer = await _ask(client, f"Làm sao đăng ký gửi xe máy {unique}?")
            rated = await client.put(
                f"/api/v1/viga/messages/{answer['message_id']}/feedback", json={"rating": "DOWN", "reason": "MISSING"}
            )
            assert rated.status_code == 200

        async with client_for(app) as client:
            await login(client, hr)
            group = [
                g for g in (await client.get("/api/v1/portal/viga-feedback")).json() if unique in g["question_text"]
            ][0]
            supplement_url = f"/api/v1/portal/viga-feedback/{group['id']}/supplement"
            recheck_url = f"/api/v1/portal/viga-feedback/{group['id']}/recheck"

            assert (await client.post(supplement_url, json={"answer": "ok"})).status_code == 422  # quá ngắn
            created = await client.post(
                supplement_url,
                json={"answer": "Đăng ký gửi xe máy tại phòng Hành chính tầng 3.", "contact": "Phòng Hành chính"},
            )
            assert created.status_code == 202, created.text
            assert created.json()["version_label"] == "Bổ sung 1"

            # Hỏi lại khi Viga vẫn chưa trả lời được: để mở, không đóng nhóm
            miss = await client.post(recheck_url)
            assert miss.status_code == 200 and miss.json()["answered"] is False and miss.json()["closed"] == 0
            still = [
                g for g in (await client.get("/api/v1/portal/viga-feedback")).json() if unique in g["question_text"]
            ]
            assert len(still) == 1 and not still[0]["resolved"]

        async with client_for(app) as client:
            await login(client, far_hr)
            assert (
                await client.post(supplement_url, json={"answer": "Câu trả lời của phòng khác."})
            ).status_code == 404
            assert (await client.post(recheck_url)).status_code == 404

        async with client_for(app) as client:
            await login(client, employee)
            assert (
                await client.post(supplement_url, json={"answer": "Nhân viên không được bổ sung."})
            ).status_code == 403
    finally:
        app.dependency_overrides.pop(get_storage_port, None)
        async with session_factory() as session:
            document = await session.scalar(select(Document).where(Document.source_key == key))
            if document is not None:
                version_ids = list(
                    (
                        await session.scalars(
                            select(DocumentVersion.id).where(DocumentVersion.document_id == document.id)
                        )
                    ).all()
                )
                await session.execute(delete(Job).where(Job.document_version_id.in_(version_ids)))
                await session.execute(delete(DocumentVersion).where(DocumentVersion.id.in_(version_ids)))
                await session.execute(delete(Document).where(Document.id == document.id))
            await session.execute(delete(AuditLog).where(AuditLog.actor_id.in_([hr.id, far_hr.id])))
            await session.commit()
