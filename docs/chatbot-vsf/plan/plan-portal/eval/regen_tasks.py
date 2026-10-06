# -*- coding: utf-8 -*-
"""Sinh lại lộ trình bằng AI qua đúng luồng thật (HR đăng nhập -> tạo lộ trình/ngày -> việc nền AI đề xuất -> chấp nhận theo thứ tự).

Chạy sau khi dọn task cũ (xem báo cáo, mục 12). Giống giao diện: tiên quyết theo tên của AI được đổi thành mã task đã tạo trước đó.
Ghi kết quả ra `regen_result.json` để so sánh với tài liệu nguồn. Mật khẩu đọc từ registry dev, không in ra.
"""
import json
import sys
import time
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000"
HERE = Path(__file__).resolve().parent
USERS = HERE.parents[2] / "data" / "registry" / "users.json"
OUT = HERE / "regen_result.json"
PUBLISH = "--publish" in sys.argv
ONLY_DOCS = {int(arg.split("=", 1)[1]) for arg in sys.argv if arg.startswith("--doc=")}  # vd. --doc=1 chỉ lấy tài liệu mã 1


def password_of(email: str) -> str:
    for user in json.loads(USERS.read_text(encoding="utf-8")):
        if user.get("email") == email:
            return user["password_dev_only"]
    raise SystemExit("không thấy tài khoản")


def main() -> None:
    client = httpx.Client(base_url=BASE, timeout=120)
    email = "hr1@vsf-demo.example"
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password_of(email)})
    assert login.status_code == 200, login.status_code

    documents = client.get("/api/v1/portal/documents").json()
    versions = [
        d["latest_version_id"]
        for d in documents
        if d["status"] == "ACTIVE" and d["latest_version_id"] and (not ONLY_DOCS or d["id"] in ONLY_DOCS)
    ]
    print("tài liệu:", [(d["id"], d["title"], d["latest_version_id"]) for d in documents])

    template = client.post(
        "/api/v1/portal/journey-templates", json={"code": f"tpl-{int(time.time())}", "title": "Lộ trình onboarding"}
    ).json()
    stage = client.post(
        f"/api/v1/portal/journey-templates/{template['id']}/stages", json={"title": "Ngày 1", "sort_order": 1}
    ).json()
    print("lộ trình", template["id"], "ngày", stage["id"])

    job = client.post("/api/v1/portal/ai/task-proposal-jobs", json={"document_version_ids": versions}).json()
    started = time.time()
    while True:
        current = client.get(f"/api/v1/portal/jobs/{job['id']}").json()
        if current["status"] in ("SUCCEEDED", "FAILED"):
            break
        if time.time() - started > 600:
            raise SystemExit("việc nền quá lâu")
        time.sleep(2)
    seconds = round(time.time() - started, 1)
    print("việc nền:", current["status"], f"{seconds}s", current.get("error"))
    if current["status"] != "SUCCEEDED":
        raise SystemExit(1)

    merged: list[dict] = []
    documents_result = current["result"]["documents"]
    for entry in documents_result:
        print(
            "-",
            entry["document_title"],
            entry["status"],
            len(entry["proposals"]),
            "đề xuất; mục chưa có task:",
            [item["heading"] for item in entry.get("uncovered_sections", [])],
        )
        for proposal in entry["proposals"]:
            if all(item["title"] != proposal["title"] for item in merged):
                merged.append({**proposal, "_document": entry["document_title"], "_version_id": entry["version_id"]})

    created: dict[str, int] = {}
    for proposal in merged:
        depends = [created[name] for name in proposal.get("prerequisites", []) if name in created]
        body = {
            "title": proposal["title"],
            "instructions_markdown": proposal["instructions_markdown"],
            "required": True,
            "source_chunks": [{"document_section_id": c["document_section_id"], "quote": c["quote"]} for c in proposal["source_chunks"]],
            "summary": proposal["summary"],
            "done_criteria": proposal["done_criteria"],
            "estimated_minutes": proposal["estimated_minutes"],
            "warnings": proposal["warnings"],
            "task_group": proposal.get("task_group"),
            "depends_on": depends,
        }
        response = client.post(f"/api/v1/portal/stages/{stage['id']}/tasks/from-proposal", json=body)
        assert response.status_code == 200, (proposal["title"], response.status_code, response.text[:200])
        created[proposal["title"]] = response.json()["id"]

    if PUBLISH:
        published = client.post(f"/api/v1/portal/journey-templates/{template['id']}/publish")
        print("xuất bản:", published.status_code)

    tree = client.get("/api/v1/portal/journey-templates/mine").json()
    nodes = [t for t in tree if t["id"] == template["id"]][0]
    tasks = nodes["stages"][0]["tasks"]
    titles = {t["id"]: t["title"] for t in tasks}
    summary = [
        {
            "order": t["sort_order"],
            "title": t["title"],
            "group": t["task_group"],
            "depends_on": [titles.get(d, d) for d in t["depends_on"]],
            "sources": [{"heading": s["section_heading"], "quote": s["quote"], "doc": s["document_title"]} for s in t.get("sources", [])],
            "body": t["body_markdown"],
        }
        for t in tasks
    ]
    OUT.write_text(
        json.dumps({"seconds": seconds, "documents": documents_result, "tasks": summary}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    for item in summary:
        print(f"{item['order']:>2}. {item['title']} [{item['group']}] sau: {item['depends_on']} · nguồn: {len(item['sources'])}")


main()
