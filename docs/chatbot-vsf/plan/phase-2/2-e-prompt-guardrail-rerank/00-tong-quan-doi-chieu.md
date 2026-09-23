# Phần 1/8 — Đối chiếu pipeline R-A-G đã code với mô hình chuẩn

> Xem [mục lục README](README.md). **Chưa code gì — chờ duyệt.**

Mô hình chuẩn (slide `day08-rag-pipeline`, `D:\AI_Action_lythuyet\slide`): `Retrieval (dense+sparse+RRF+
rerank) → Augmentation (structure, order, metadata, token budget, conflict rule) → Generation (ground,
self-check, abstain) → Eval (RAGAS: Recall/Faithfulness/Relevance)`.

| Lớp | Chuẩn yêu cầu | Đã có trong code (2-C/2-D) | Đánh giá |
|---|---|---|---|
| Retrieval | Dense + Sparse + RRF | `hybrid_search.py`: BM25 (`@@@`) + dense (`<=>`) + RRF (k=60) | ✅ Đủ |
| Retrieval | Rerank (cross-encoder) trên top-K sau fusion | Không có — RRF là bước cuối | ⚠️ Đã có quyết định D5 cũ: chưa bật, xem [01-retrieval-rerank.md](01-retrieval-rerank.md) |
| Retrieval | Pre-filter theo metadata trước search | Có: lọc `status='ACTIVE'`, `effective_from/to` (as_of), `embedding_model_version` ngay trong SQL | ✅ Đủ |
| Retrieval | Query expansion/decomposition | Có: `query_rewrite.py` tách nhiều ý — tương đương "Decomposition" trong slide, nhưng **không giới hạn** số/độ dài câu con | ⚠️ Xem [03 mục 4.3](03-generation-guardrail-tien-kiem.md) |
| Augmentation | Tách System/Context/Question rõ ràng | Có nhưng chưa đủ chặt (nối `"\n\n"` thuần, không có tag) | ⚠️ Xem [02-augmentation.md](02-augmentation.md) mục 3.1 |
| Augmentation | Thứ tự chống "lost in the middle" | Section đưa vào theo đúng thứ tự RRF | ✅ Giữ nguyên có chủ đích — chưa có số đo để đổi, xem [02-augmentation.md](02-augmentation.md) mục 3.2 |
| Augmentation | Metadata trong context (nguồn, ngày, version) | Có `document_title`, `heading`, thiếu `version_label` trong context đưa cho LLM | ⚠️ Bổ sung nhỏ |
| Augmentation | Token budget (context ≤ ~60%) | Có `SECTION_TOKEN_BUDGET=3000` nhưng chưa đối chiếu với budget tổng | ⚠️ Xem [02-augmentation.md](02-augmentation.md) mục 3.4 |
| Augmentation | Conflict rule (ưu tiên nguồn mới) | Xử lý ở tầng DB: chỉ 1 version `ACTIVE` cho mỗi `as_of` (INV3) | ✅ Đủ, do schema xử lý từ gốc |
| Generation | Grounded, cấm bịa | Có, rõ trong `SYSTEM_PROMPT` của `answer_service.py` | ✅ Đủ |
| Generation | Self-check / validator | Có: `validator.py` (INV6, INV13) — cùng logic `verified_substring` của Ralion. **Lưu ý**: chỉ chứng minh `quote` có thật, KHÔNG chứng minh `text` diễn giải đúng — xem [05-eval.md](05-eval.md) | ⚠️ Đủ cho guardrail hậu kiểm, KHÔNG đủ để coi là "faithfulness đã được bảo đảm" |
| Generation | Abstain rõ ràng, gợi ý bước tiếp | Có `NO_BASIS` nhưng chưa gợi ý hành động tiếp theo trong `text` | ⚠️ Bổ sung nhỏ, đã có ở tầng frontend (`chat.noSource`) |
| Eval | RAGAS triad (Recall/Faithfulness/Relevance) | Chưa đo cụ thể — mới có kế hoạch "10 câu hỏi golden set" ở `phase-2.md` mục 4 | ⚠️ Xem [05-eval.md](05-eval.md) |
| Guardrail tiền kiểm | Injection defense | Có 1 dòng ở `answer_service.py`, KHÔNG có ở `query_rewrite.py` (chạm input thô của user đầu tiên) | ⚠️ Xem [03 mục 4.1](03-generation-guardrail-tien-kiem.md) |
| Guardrail tiền kiểm | Input validation | `ChatAskRequestDTO.question` **đã có** `min_length=1, max_length=2000` — chỉ thiếu chặn chuỗi toàn khoảng trắng | ⚠️ Xem [03 mục 4.2](03-generation-guardrail-tien-kiem.md) |
| Guardrail tiền kiểm | Giới hạn kết quả rewrite | Không có — `standalone_questions[]` không giới hạn số lượng/độ dài | ⚠️ Xem [03 mục 4.3](03-generation-guardrail-tien-kiem.md) — ưu tiên cao nhất trong đợt sửa này |
| Guardrail tiền kiểm | Rate limit | Không có cho `/chat/ask` (chỉ `auth_router` có) | ⚠️ Xem [03 mục 4.4](03-generation-guardrail-tien-kiem.md) |
| Guardrail hậu kiểm | Output validation | Có (`validator.py`) | ✅ Đủ cho phần trích dẫn, xem lưu ý faithfulness ở trên |

**Kết luận chung**: khung R-A-G cốt lõi (retrieval hybrid, grounding, validator hậu kiểm) đã đúng chuẩn và
không cần sửa lại kiến trúc. Sau khi đối chiếu lại với code thật (đợt review "codex"), việc quan trọng nhất
không phải đảo thứ tự context hay bật rerank (cả hai đều chưa có số đo chứng minh cần) mà là: (1) chặn
`standalone_questions[]` không giới hạn — lỗ hổng tốn tài nguyên rõ ràng nhất, (2) vá chống injection còn
thiếu ở `query_rewrite.py`, (3) thêm rate-limit cho endpoint tốn tiền. Không có lỗ hổng kiến trúc lớn nào
cần đập đi làm lại.
