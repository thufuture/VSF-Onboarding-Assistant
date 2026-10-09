"""GET /portal/documents/{id}/versions/{vid}/compare: so phiên bản với bản trước (chỉ đọc, chỉ HR/Admin)."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from portal_docs_fixtures import (  # noqa: F401  (fixture được pytest tìm theo tên trong module này)
    MakeMember,
    app,
    category,
    cleanup_documents,
    client_for,
    login,
    make_member,
    session_factory,
    team,
)
from test_portal_document_versions_api import upload

pytestmark = pytest.mark.integration

BODIES = [
    f"Nội dung điều số {i} có nhiều chữ khác nhau để thành một đoạn riêng. " * 12 + f"Mã {i}." for i in range(1, 5)
]


def build_doc(bodies: list[str]) -> str:
    return "# Quy định thử\n\n" + "\n\n".join(f"## Điều {i}\n\n{body}" for i, body in enumerate(bodies, start=1))


async def test_compare_reports_changed_sections_and_estimate(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
) -> None:
    hr = await make_member("HR", team.id)
    source_key = f"cmp-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)
    edited = list(BODIES)
    edited[1] = edited[1].replace("Mã 2.", "Mã 2 đã sửa.")
    edited.append("Điều mới hoàn toàn nói về quy trình bàn giao thiết bị khi nghỉ việc. " * 10)

    async with client_for(app) as client:
        await login(client, hr)
        first = (await upload(client, category, source_key, label="v1", content=build_doc(BODIES))).json()
        doc_id, v1 = first["document_id"], first["document_version_id"]

        alone = (await client.get(f"/api/v1/portal/documents/{doc_id}/versions/{v1}/compare")).json()
        assert alone["has_base"] is False and alone["sections"] == [] and alone["recompute"] is None

        second = (
            await upload(client, category, source_key, label="v2", content=build_doc(edited), document_id=doc_id)
        ).json()
        v2 = second["document_version_id"]
        response = await client.get(f"/api/v1/portal/documents/{doc_id}/versions/{v2}/compare")
        assert response.status_code == 200, response.text
        body = response.json()

    assert body["has_base"] and body["base_version_id"] == v1 and body["base_version_label"] == "v1"
    assert body["base_reason"] == "previous_revision"
    assert (body["added"], body["removed"], body["modified"]) == (1, 0, 1)
    modified = next(s for s in body["sections"] if s["status"] == "modified")
    assert modified["heading"] == "Điều 2" and any(seg["op"] == "insert" for seg in modified["segments"])
    unchanged = [s for s in body["sections"] if s["status"] == "unchanged"]
    assert unchanged and all(s["segments"] == [] for s in unchanged)
    assert 0 < body["recompute"]["chunks_to_embed"] < body["recompute"]["chunks_total"]


async def test_compare_requires_staff_and_valid_version(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
) -> None:
    hr = await make_member("HR", team.id)
    employee = await make_member("USER", team.id)
    source_key = f"cmp-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)

    async with client_for(app) as client:
        await login(client, hr)
        first = (await upload(client, category, source_key, label="v1", content=build_doc(BODIES))).json()
        doc_id, v1 = first["document_id"], first["document_version_id"]
        missing = await client.get(f"/api/v1/portal/documents/{doc_id}/versions/{v1 + 100000}/compare")
        assert missing.status_code == 404
        wrong_base = await client.get(f"/api/v1/portal/documents/{doc_id}/versions/{v1}/compare?base_version_id={v1}")
        assert wrong_base.status_code == 404

    async with client_for(app) as client:
        await login(client, employee)
        forbidden = await client.get(f"/api/v1/portal/documents/{doc_id}/versions/{v1}/compare")
        assert forbidden.status_code == 403
