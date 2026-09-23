# 2-E-7 — Việc cụ thể sẽ code (sau khi duyệt) và việc KHÔNG làm

> Phần 7/8. Xem [mục lục README](README.md). **Chưa code — chờ duyệt.**

## Việc sẽ code, đúng thứ tự ưu tiên đã chốt lại

> Thứ tự dưới đây đã sửa theo góp ý (codex): giới hạn `standalone_questions[]` lên trước vì là lỗ hổng tốn
> tài nguyên rõ ràng nhất; đảo thứ tự context bị đẩy xuống backlog (xem [02-augmentation.md](02-augmentation.md)
> mục 3.2), không còn nằm trong đợt sửa này.

1. `backend/src/dto/request/chat_request_dto.py`: thêm `field_validator` strip + từ chối chuỗi toàn khoảng
   trắng sau `.strip()` cho `question` (`min_length=1, max_length=2000` đã có sẵn, không cần thêm)
   ([03 mục 4.2](03-generation-guardrail-tien-kiem.md)).
2. `backend/src/services/chat/query_rewrite.py`: thêm `MAX_SUBQUESTIONS`/`MAX_SUBQUESTION_LENGTH`, cắt/
   fallback về `[question gốc]` khi kết quả bất thường; thêm dòng chống injection vào `SYSTEM_PROMPT`, bọc
   câu hỏi thô trong `<user_input>` qua `guardrail_input.wrap_user_input()`
   ([03 mục 4.1, 4.3](03-generation-guardrail-tien-kiem.md); tên file mới xem
   [07-cay-thu-muc-code.md](07-cay-thu-muc-code.md)).
3. `backend/src/services/chat/chat_throttle.py` (mới, tái dùng `LoginThrottle` nguyên trạng, đổi tên biến cho
   đúng ngữ cảnh "câu hỏi/cửa sổ" thay vì "thử sai/khóa"): instance riêng, khóa theo `user_id`
   ([03 mục 4.4](03-generation-guardrail-tien-kiem.md)).
4. `backend/src/api/routers/chat_router.py`: gắn throttle vào đầu `ask()`, trả 429 kèm `Retry-After` khi vượt.
5. `backend/src/api/dependencies.py`: thêm `get_chat_throttle` (singleton trên `app.state`, giống pattern
   `LoginThrottle` hiện có cho auth).
6. `backend/src/services/chat/prompt_builder.py` (mới, tách khỏi `answer_service.py`): bọc
   `<context>`/`<question>`, thêm `document_title`/`version_label` vào dòng tiêu đề mỗi đoạn — **giữ nguyên
   thứ tự RRF** (không đảo, xem [02-augmentation.md](02-augmentation.md) mục 3.2).
7. `backend/src/services/retrieval/rerank.py` (mới, passthrough — xem
   [07-cay-thu-muc-code.md](07-cay-thu-muc-code.md)): chỗ cắm sẵn, không bật thật, đúng quyết định D5 cũ
   ([01-retrieval-rerank.md](01-retrieval-rerank.md)).
8. `backend/tests/`: test injection-defense text tồn tại trong system prompt của cả `query_rewrite.py` và
   `answer_service.py` (assert chuỗi), test giới hạn/fallback `standalone_questions[]`, test throttle (429
   sau N lần trong cửa sổ), test `prompt_builder` có đúng tag + metadata + **giữ nguyên thứ tự RRF**, test
   `rerank.py` passthrough trả nguyên input.
9. Không đổi `hybrid_search.py`/`validator.py` (đã đủ, xem [00-tong-quan-doi-chieu.md](00-tong-quan-doi-chieu.md)).
10. Cập nhật `bao-cao-phase-2.md` (khi chạy golden set) với bảng RAGAS triad ở [05-eval.md](05-eval.md) —
    lưu ý Faithfulness vẫn cần đọc tay `claim.text`, không chỉ đếm tỷ lệ NO_BASIS do quote sai (mục đính
    chính ở [05-eval.md](05-eval.md)).

## KHÔNG làm trong đợt sửa này (backlog rõ ràng, không lẫn vào scope)

- Cross-encoder rerank thật ([01-retrieval-rerank.md](01-retrieval-rerank.md)) — đúng quyết định D5 cũ, chỉ
  bật khi đo Recall@5 golden-set không đạt.
- Đảo thứ tự context "best-first-and-last" ([02-augmentation.md](02-augmentation.md) mục 3.2) — chờ số đo.
- Guardrail scope riêng bằng LLM/rule-based trước retrieval ([03 mục 4.5](03-generation-guardrail-tien-kiem.md)).
- Thư viện guardrail chuyên dụng ([04-bao-mat.md](04-bao-mat.md)).
- Thư viện `ragas` tự động ([05-eval.md](05-eval.md)) — chấm tay đủ cho 10 câu, kể cả faithfulness.
- Multi-worker rate-limit chia sẻ (Redis...) — giữ in-process như `LoginThrottle` hiện tại, đúng giả định
  MVP 1 worker đã ghi trong `login_throttle.py`.
