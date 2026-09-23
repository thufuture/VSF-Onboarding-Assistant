# 2-E-5 — Bảo mật & log (rà theo OWASP Top 10 cho LLM, rút gọn cho MVP)

> Phần 5/7. Xem [mục lục ở 2-e-1](00-tong-quan-doi-chieu.md). **Chưa code — chờ duyệt.**

| Rủi ro (OWASP LLM Top 10) | Đã xử lý | Còn thiếu |
|---|---|---|
| LLM01 Prompt Injection | 1 dòng ở `answer_service.py` | Thiếu ở `query_rewrite.py`, xem [2-e-4](03-generation-guardrail-tien-kiem.md) mục 4.1 |
| LLM02 Sensitive Info Disclosure | Prompt cấm trả lời thông tin cá nhân (`out_of_scope`) | — |
| LLM04 Model DoS (spam gọi tốn tiền) | — | Rate-limit, xem [2-e-4](03-generation-guardrail-tien-kiem.md) mục 4.3 |
| LLM06 Sensitive Info trong log | Langfuse chỉ nhận metadata, không nội dung (INV8, đã xác nhận với bạn) | Đã kiểm `chat_router.py`: không có `logger.info(question)`/log nội dung nào — giữ nguyên |
| LLM09 Overreliance | Validator ép NO_BASIS khi quote sai | — |

## Quyết định: không thêm thư viện guardrail chuyên dụng

Không đưa thêm thư viện guardrail chuyên dụng (`guardrails-ai`, `nemo-guardrails`, `rebuff`...) — quy mô MVP
nhỏ, logic cần (injection-defense text, độ dài input, rate-limit, verbatim-quote validator) đã tự viết đủ,
ít dòng, dễ audit hơn là thêm dependency nặng phải học cấu hình riêng trong 4 tuần. Ghi vào backlog nếu sau
này mở rộng nhiều loại tài liệu/rủi ro hơn.
