# -*- coding: utf-8 -*-
"""Bộ 26 câu hỏi Viga trên hai tài liệu thật; mỗi câu một cuộc hội thoại mới (không dính lịch sử). Chỉ đọc, không sửa dữ liệu.

Chạy: `python viga_eval.py [--out viga_eval_after.json]` (cần backend đang chạy; mật khẩu đọc từ registry dev, không in ra).
Kết quả mỗi câu: ✓ đúng loại và đủ các ý bắt buộc; ~ đúng loại nhưng thiếu ý, hoặc dán cả khối task, hoặc còn ký hiệu Markdown thô; ✗ sai loại.
"""
import json
import re
import sys
import time
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000"
HERE = Path(__file__).resolve().parent
USERS = HERE.parents[2] / "data" / "registry" / "users.json"
OUT = HERE / (sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "viga_eval.json")

# (id, tài liệu, câu hỏi, kỳ vọng: "ANSWER" | "NO_BASIS" | "ANY" (đáp án một phần/chưa quy định đều chấp nhận), các ý bắt buộc)
CASES = [
    (1, "D1", "Hồ sơ cần nộp trong ngày đầu gồm những gì?", "ANSWER", ["cv", "lý lịch tư pháp", "khám sức khỏe", "nơi cư trú", "căn cước", "chứng chỉ"]),
    (2, "D1", "Nộp hồ sơ ngày đầu thì liên hệ đầu mối nào?", "ANSWER", ["phòng tuyển dụng"]),
    (3, "D1", "Chương trình Đào tạo Hội nhập có bắt buộc không và điều kiện hoàn thành là gì?", "ANSWER", ["bắt buộc", "điểm danh", "khảo sát", "80"]),
    (4, "D1", "Bài test cuối khóa phải đạt bao nhiêu phần trăm?", "ANSWER", ["80"]),
    (5, "D1", "Đầu mối của chương trình Đào tạo Hội nhập là ai, email gì?", "ANSWER", ["v.thudq@vinsmartfuture.tech"]),
    (6, "D1", "Khi nào tôi ký hợp đồng lao động?", "ANSWER", ["email", "cuối ngày"]),
    (7, "D1", "Đăng ký faceid chấm công ở đâu?", "ANSWER", ["tầng 14", "vincom"]),
    (8, "D1", "Tôi nhận laptop ở đâu?", "ANSWER", ["tầng 12", "ithd"]),
    (9, "D1", "Nhận laptop xong thì làm gì tiếp theo?", "ANSWER", ["outlook", "teams"]),
    (10, "D1", "Viết email hỗ trợ cho ITHD thì gửi tới địa chỉ nào và đặt tiêu đề thế nào?", "ANSWER", ["support@vinsmartfuture.tech", "ithd"]),
    (11, "D1", "Trước khi viết ticket tôi cần kiểm tra gì?", "ANSWER", ["quick access"]),
    (12, "D1", "Muốn dùng VPN hoặc xin exception USB thì cần ai đồng thuận?", "ANSWER", ["t3"]),
    (13, "D1", "Máy tôi đã dùng sẵn Ubuntu thì xin phê duyệt thế nào?", "ANSWER", ["team", "chụp"]),
    (14, "D1", "Sau khi VinSOC phản hồi email thì tôi làm gì?", "ANSWER", ["ticket", "ithd", "tầng 14"]),
    (15, "D1", "Yêu cầu tủ gửi đồ như thế nào?", "ANSWER", ["tủ gửi đồ"]),
    (16, "D2", "Tôi chưa có lý lịch tư pháp thì sao?", "ANSWER", ["giấy hẹn"]),
    (17, "D2", "Tôi chỉ có CMND, không có căn cước công dân thì thay được không?", "ANY", []),
    (18, "D2", "T3 chưa trả lời email phê duyệt thì tôi làm sao?", "ANSWER", ["1 ngày", "nhắc"]),
    (19, "D2", "Có bắt buộc làm chuỗi yêu cầu ngoại lệ như Ubuntu, VPN, USB không?", "ANSWER", ["không"]),
    (20, "D2", "Văn phòng của tôi không phải Vincom Đồng Khởi thì đăng ký faceid thế nào?", "ANY", []),
    (21, "D1", "tôi ở hồ chí minh checkin ở đâu á", "ANY", ["onboard"]),
    (22, "D2", "Tôi chỉ có CMND, không có căn cước công dân, có thay được không?", "ANY", []),
    (23, "D2", "tôi không có căn cước công dân sài vnid được không", "ANY", []),
    (24, "D1", "Check-in ngày đầu làm thế nào?", "ANY", ["onboard"]),
    (25, "D1", "Tôi làm ở Hà Nội thì check-in ở đâu?", "ANY", ["onboard"]),
    (26, "D1", "Tôi không có VNeID thì nộp giấy xác nhận nơi cư trú thế nào?", "ANSWER", ["photo", "phòng tuyển dụng"]),
]

RAW_TASK_DUMP = re.compile(r"##\s*(Vì sao phải làm|Các bước|Điều kiện hoàn thành)")
RAW_MARKDOWN = re.compile(r"\*\*|^\s*\*\s|\\\*|\\_")


def password_of(email: str) -> str:
    for user in json.loads(USERS.read_text(encoding="utf-8")):
        if user.get("email") == email:
            return user["password_dev_only"]
    raise SystemExit("không thấy tài khoản")


def main() -> None:
    email = "newhire1@vsf-demo.example"
    client = httpx.Client(base_url=BASE, timeout=120)
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password_of(email)})
    assert login.status_code == 200, login.status_code
    client.get("/api/v1/portal/me/journey")  # tạo lộ trình của nhân viên từ bản đã xuất bản (như khi mở trang), để công cụ lộ trình có dữ liệu
    results = []
    for case_id, doc, question, expect, must in CASES:
        started = time.perf_counter()
        response = client.post("/api/v1/viga/ask", json={"question": question})
        seconds = round(time.perf_counter() - started, 1)
        body = response.json() if response.status_code == 200 else {"error": response.text[:200]}
        claims = body.get("claims", [])
        text = " ".join([body.get("message", "")] + [c.get("text") or "" for c in claims] + [c.get("quote") or "" for c in claims]).lower()
        answered = body.get("response_type") == "ANSWER" and any(c["response_type"] == "ANSWER" for c in claims)
        got = "ANSWER" if answered else "NO_BASIS"
        missing = [m for m in must if m.lower() not in text]
        dump = bool(RAW_TASK_DUMP.search(body.get("message", "") + " ".join(c.get("text") or "" for c in claims)))
        raw_markdown = bool(RAW_MARKDOWN.search(" ".join(c.get("text") or "" for c in claims) + " " + " ".join(c.get("quote") or "" for c in claims)))
        type_ok = expect == "ANY" or got == expect
        verdict = "✓" if type_ok and not missing and not dump and not raw_markdown else ("~" if type_ok else "✗")
        results.append(
            {
                "id": case_id, "doc": doc, "question": question, "expect": expect, "status": response.status_code,
                "type": body.get("response_type"), "route": body.get("route"), "got": got, "verdict": verdict, "seconds": seconds,
                "missing": missing, "task_dump": dump, "raw_markdown": raw_markdown, "unanswered": body.get("unanswered", []),
                "can_report": body.get("can_report_to_hr"), "message": body.get("message"),
                "claims": [
                    {"type": c["response_type"], "text": c.get("text"), "quote": c.get("quote"),
                     "source": (c.get("source") or {}).get("section_heading"), "doc": (c.get("source") or {}).get("document_title")}
                    for c in claims
                ],
            }
        )
        print(case_id, verdict, got, "thiếu:", missing, "dump" if dump else "", "md" if raw_markdown else "", f"{seconds}s", flush=True)
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    ok = sum(r["verdict"] == "✓" for r in results)
    part = sum(r["verdict"] == "~" for r in results)
    print(f"Tổng: {ok} ✓, {part} ~, {len(results) - ok - part} ✗ trên {len(results)} câu → {OUT.name}")


main()
