# 2-E-7 — Cây thư mục backend: tách file theo đúng giai đoạn R-A-G-Guardrail

> Phần bổ sung. Xem [mục lục README](README.md). **Chưa code — chờ duyệt.**

Mục [06-viec-can-code.md](06-viec-can-code.md) liệt kê việc sửa theo mô tả; file này chốt **tên file cụ thể**
và **file nào mới/file nào sửa**, để khi code không phải đoán đặt tên gì. Tách nhỏ theo từng giai đoạn (R/A/G/
Guardrail) — mỗi quan tâm một file, đúng tinh thần slide `day08-rag-pipeline`, dễ tìm khi debug ("lỗi ở
Retrieval hay Generation?" → đúng luôn thư mục/file).

```text
backend/src/services/
├── retrieval/
│   ├── hybrid_search.py        # ĐÃ CÓ — BM25 + dense + RRF (không đổi)
│   └── rerank.py                # MỚI — passthrough, KHÔNG bật thật (xem 01-retrieval-rerank.md)
│
└── chat/
    ├── query_rewrite.py         # ĐÃ CÓ — SỬA: thêm injection-guard qua guardrail_input.wrap_user_input()
    ├── prompt_builder.py        # MỚI — tách khỏi answer_service: dựng <context>/<question>, thứ tự
    │                             #        best-first-and-last, metadata nguồn (xem 02-augmentation.md)
    ├── answer_service.py        # ĐÃ CÓ — SỬA: bỏ _build_user_prompt, gọi prompt_builder.build() thay vào
    ├── validator.py             # ĐÃ CÓ — không đổi (đã là guardrail hậu kiểm, INV6/INV13)
    ├── guardrail_input.py       # MỚI — injection-defense text dùng chung + wrap_user_input() (tag <user_input>)
    └── chat_throttle.py         # MỚI — rate-limit /chat/ask, tái dùng LoginThrottle (xem 03-...md mục 4.3)
```

## Vì sao có `rerank.py` dù quyết định KHÔNG bật (mục 01)

Tạo file rỗng/passthrough thay vì không tạo gì, để:
1. Chỗ cắm sẵn khi Phase 7 cần bật thật (theo đúng quy trình chẩn đoán RAGAS ở [05-eval.md](05-eval.md)) —
   không phải sửa lại `hybrid_search.py`/`search_to_sections` để chèn thêm bước.
2. Code đọc dễ hiểu luồng đủ 3 giai đoạn R (search → rerank → done) dù bước giữa hiện là no-op, thay vì luồng
   thiếu hẳn một bước mà người đọc sau phải tự suy luận là "quên" hay "cố ý bỏ".

Nội dung dự kiến (không làm gì khác ngoài trả nguyên input — không gọi model, không thêm latency thật):

```python
# backend/src/services/retrieval/rerank.py
"""Chỗ cắm rerank (cross-encoder) cho tương lai — HIỆN CHƯA BẬT.

Quyết định không dùng rerank cho MVP: xem docs/chatbot-vsf/plan/phase-2/2-e-prompt-guardrail-rerank/
01-retrieval-rerank.md. Hàm này là passthrough để `search_to_sections` gọi đúng đủ 3 bước
(search → rerank → done) mà không phải sửa lại chỗ gọi khi bật rerank thật sau này.
"""

from src.services.retrieval.hybrid_search import SectionEvidence


def rerank(sections: list[SectionEvidence], *, query: str) -> list[SectionEvidence]:  # noqa: ARG001
    return sections
```

## Vì sao tách `prompt_builder.py` khỏi `answer_service.py`

`answer_service.py` hiện vừa build prompt (`_build_user_prompt`) vừa gọi LLM vừa parse kết quả — 3 trách
nhiệm khác nhau. Sau khi thêm delimiter/metadata/thứ tự ([02-augmentation.md](02-augmentation.md)), phần build
prompt đủ phức tạp để tách riêng, test riêng (không cần mock LLM để test cách sắp xếp context) — khớp cách
`chat_router.py` đã tách `_evidence_for_question`/`_resolve_source` thành hàm riêng thay vì nhồi hết vào `ask()`.

## Vì sao tách `guardrail_input.py` thay vì sửa thẳng trong `query_rewrite.py`

Injection-defense text hiện lặp ý tưởng ở cả `query_rewrite.py` (sắp thêm) và `answer_service.py` (đã có,
dạng câu riêng trong `SYSTEM_PROMPT`). Tách `guardrail_input.py` giữ một chuỗi hằng số
(`INJECTION_DEFENSE_NOTE`) dùng chung cho cả 2 nơi + hàm `wrap_user_input(text: str) -> str` (bọc
`<user_input>...</user_input>`) — sửa 1 chỗ khi cần chỉnh câu chữ, không lệch giữa 2 file.

## Test tương ứng (đặt cùng cấu trúc, dễ đối chiếu)

```text
backend/tests/test_chat/
├── test_query_rewrite.py        # ĐÃ CÓ — thêm: assert injection-guard có trong prompt thật gửi đi
├── test_prompt_builder.py       # MỚI — thứ tự best-first-and-last, có tag, có metadata nguồn
├── test_answer_service.py       # ĐÃ CÓ — không đổi nhiều (giờ mock prompt_builder.build() thay vì check string)
├── test_guardrail_input.py      # MỚI — wrap_user_input() bọc đúng tag, hằng số không rỗng
└── test_chat_throttle.py        # MỚI — 429 sau N lần/cửa sổ, khóa theo user_id, reset đúng cửa sổ

backend/tests/test_retrieval/
└── test_rerank.py               # MỚI — passthrough trả đúng nguyên list, không đổi thứ tự/nội dung
```
