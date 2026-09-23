# Bổ sung/hardening sau 2-C/2-D — Prompt system chuẩn, Guardrail, Rerank (chưa làm, chờ duyệt)

> **Không đổi nghĩa checkpoint "2-E" của [phase-2.md](../phase-2.md) mục 5** (2-E ở đó = "Endpoint và trang
> chat tối giản", đã xong). Đây là tài liệu **bổ sung/hardening** sau khi 2-C/2-D
> ([2-c-2-d-tim-kiem-va-tra-loi-ke-hoach-chi-tiet.md](../2-c-2-d-tim-kiem-va-tra-loi-ke-hoach-chi-tiet.md))
> đã code xong — rà pipeline runtime (R-A-G) đã code so với mô hình chuẩn (slide `day08-rag-pipeline`,
> `D:\AI_Action_lythuyet\slide`) và pattern bảo mật/guardrail của Ralion (`P-040`). Tên thư mục giữ tiền tố
> `2-e-` chỉ vì lịch sử đặt tên, không phải checkpoint mới trong lộ trình. **Chưa code gì — chờ duyệt.**
>
> Đã sửa theo góp ý đối chiếu code thật (đợt review "codex"): đính chính DTO đã có `min/max_length`
> ([03 mục 4.2](03-generation-guardrail-tien-kiem.md)), thêm giới hạn `standalone_questions[]` là ưu tiên
> cao hơn đảo thứ tự context ([03 mục 4.3](03-generation-guardrail-tien-kiem.md)), bớt nói quá về
> faithfulness đã được validator bảo đảm ([05-eval.md](05-eval.md)), hoãn "best-first-and-last" tới khi có
> số đo ([02-augmentation.md](02-augmentation.md) mục 3.2), và xác nhận lại quyết định rerank theo đúng D5
> đã chốt trước đó ([01-retrieval-rerank.md](01-retrieval-rerank.md)).

Thư mục chia theo đúng thứ tự pipeline R-A-G-Eval:

| File | Giai đoạn | Nội dung |
|---|---|---|
| [00-tong-quan-doi-chieu.md](00-tong-quan-doi-chieu.md) | — | Bảng đối chiếu toàn bộ R-A-G-Eval-Guardrail chuẩn vs đã code |
| [01-retrieval-rerank.md](01-retrieval-rerank.md) | **R**etrieval | Rerank — quyết định KHÔNG thêm cho MVP |
| [02-augmentation.md](02-augmentation.md) | **A**ugmentation | Prompt structure: delimiter, thứ tự, metadata, token budget |
| [03-generation-guardrail-tien-kiem.md](03-generation-guardrail-tien-kiem.md) | **G**eneration + Guardrail | Chống injection, input validation, rate-limit, scope |
| [04-bao-mat.md](04-bao-mat.md) | Bảo mật | Rà OWASP LLM Top 10 |
| [05-eval.md](05-eval.md) | Eval | RAGAS triad chấm tay cho golden set |
| [06-viec-can-code.md](06-viec-can-code.md) | — | Danh sách file cụ thể sẽ sửa + backlog KHÔNG làm |
| [07-cay-thu-muc-code.md](07-cay-thu-muc-code.md) | — | Cây thư mục backend: tên file mới/sửa cụ thể (rerank.py, prompt_builder.py, guardrail_input.py, chat_throttle.py) + test tương ứng |

Đọc theo thứ tự 00 → 07.
