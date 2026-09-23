# 2-C + 2-D mở rộng — Tìm kiếm hybrid, viết lại câu hỏi, nhiều ý, theo dõi Langfuse (chưa làm, chờ duyệt)

> Thuộc [phase-2.md](phase-2.md) mục 5 (2-C, 2-D). Tài liệu này **mở rộng** 2-D so với bản gốc trong `phase-2.md`
> theo yêu cầu mới: hỗ trợ câu hỏi nhiều ý (`claims[]`), viết lại câu hỏi trước khi tìm (query rewrite/tách ý),
> và theo dõi từng bước bằng Langfuse. Phụ thuộc: **2-B đã xong** (chunk có `embedding`, `lexical_text`, `section_id`).
> **Spike BM25/vector đã chạy thật** trên DB dev (mục 2) — không còn là rủi ro chưa rõ cú pháp như `phase-2.md` lo ngại.

## 1. Tổng quan luồng mới (so với bản gốc chỉ có 1 lượt tìm, 1 answer)

```text
Câu hỏi thô của nhân sự
        │
        ▼
┌─────────────────────────────┐
│ B0. Viết lại câu hỏi (LLM)   │  rewrite_query() — 1 lời gọi LLM nhỏ, rẻ (mô hình flash, prompt ngắn)
│  - sửa lỗi chính tả/viết tắt │  Trả về: { standalone_questions: string[] }
│  - tách nhiều ý thành nhiều  │  1 ý -> mảng 1 phần tử (đa số trường hợp)
│    câu hỏi độc lập           │  Nhiều ý -> mảng nhiều phần tử
└──────────────┬───────────────┘
               │ với MỖI câu hỏi con — CHẠY SONG SONG (asyncio.gather), không tuần tự
               ▼
┌─────────────────────────────┐
│ 2-C. Tìm kiếm hybrid         │  N câu hỏi con -> N lượt tìm kiếm cùng lúc (độc lập, không câu nào
│  BM25 + vector + RRF         │  chờ câu kia; chỉ tốn thêm connection DB tạm thời, không tốn thêm LLM)
└──────────────┬───────────────┘
               │ chờ đủ N kết quả rồi gộp evidence lại (bỏ trùng section)
               ▼
┌─────────────────────────────┐
│ 2-D. Một lời gọi LLM DUY NHẤT│  đưa TẤT CẢ evidence đã gom vào 1 prompt, LLM trả claims[]
│  trả claims[] (nhiều ý)      │  mỗi claim tự đứng độc lập: có thể ANSWER, có thể "chưa có căn cứ"
└──────────────┬───────────────┘
               │
               ▼
        Validator kiểm TỪNG claim (quote đúng nguyên văn? chunk_id hợp lệ?)
               │
               ▼
        Trả về người dùng: danh sách claims, mỗi cái có trạng thái riêng
```

**Vì sao gộp lại 1 lời gọi LLM ở bước cuối** (không tách 1 lời gọi/1 ý): rẻ hơn, và LLM cần thấy toàn bộ câu hỏi gốc để không trả lời rời rạc, mất mạch (ví dụ câu hỏi có ngữ cảnh chung).

## 2. Đã spike thật (không còn đoán cú pháp)

Chạy trực tiếp trên DB dev (`document_chunks` đã có dữ liệu từ 2-B):

```sql
-- BM25 (pg_search 0.25.4) — toán tử @@@, điểm bằng paradedb.score(id)
SELECT id, chunk_index, paradedb.score(id), left(content,40)
FROM document_chunks
WHERE lexical_text @@@ 'phép'
ORDER BY paradedb.score(id) DESC LIMIT 5;
-- Kết quả thật: id=54 score=0.19070879 ... (chạy được, đúng cú pháp)

-- Dense/vector (pgvector) — toán tử <=> (cosine distance, càng nhỏ càng gần)
SELECT id, chunk_index, embedding <=> :query_vector AS dist
FROM document_chunks
ORDER BY dist LIMIT 5;
-- Kết quả thật: id=54 dist=0 (chính nó), id=53 dist=0.19 ...
```

Cú pháp khớp đúng những gì `phase-2.md` dự kiến — **rủi ro "cú pháp BM25 đổi giữa các bản" coi như đã xử lý xong**, không cần spike lại khi viết code thật.

## 3. Cột dùng trong tìm kiếm hybrid (không cột nào mới — đã có từ 2-A)

| Cột | Bảng | Dùng để |
|---|---|---|
| `lexical_text` | `document_chunks` | BM25 (`@@@`) — chữ đã tách từ, viết thường |
| `embedding` | `document_chunks` | Dense (`<=>`) — vector 1024 chiều |
| `id` | `document_chunks` | `key_field` của chỉ mục BM25; là `chunk_id` trả về cho LLM/validator (INV6) |
| `section_id` | `document_chunks` | Nối từ chunk trúng → section cha (đã giải thích ở lượt trước) |
| `version_id` (trên chunk, phi chuẩn hóa) | `document_chunks` | Lọc nhanh theo hiệu lực mà không cần join `document_sections` |
| `status`, `effective_from`, `effective_to` | `document_versions` | Lọc chỉ lấy version đang `ACTIVE` và đúng ngày hỏi (`as_of`), INV3 |
| `embedding_model_version` | `document_chunks` | Lọc chỉ so sánh vector cùng phiên bản model (INV7) — đổi model phải chạy `REINDEX`, không so lẫn |

**Không cần thêm cột hay migration nào** — mọi thứ 2-C/2-D cần đã có sẵn từ `0001_core`.

## 4. Câu truy vấn hybrid đầy đủ (kế hoạch mã, chưa chạy)

```sql
-- Nhánh BM25 (top 30)
SELECT c.id, c.section_id, paradedb.score(c.id) AS bm25_score
FROM document_chunks c
JOIN document_versions v ON v.id = c.version_id
WHERE c.lexical_text @@@ :lexical_query
  AND v.status = 'ACTIVE'
  AND v.effective_from <= :as_of
  AND (v.effective_to IS NULL OR v.effective_to >= :as_of)
  AND c.embedding_model_version = :current_model_version
ORDER BY bm25_score DESC LIMIT 30;

-- Nhánh dense (top 30) — cùng điều kiện lọc hiệu lực
SELECT c.id, c.section_id, (c.embedding <=> :query_vector) AS distance
FROM document_chunks c
JOIN document_versions v ON v.id = c.version_id
WHERE v.status = 'ACTIVE'
  AND v.effective_from <= :as_of
  AND (v.effective_to IS NULL OR v.effective_to >= :as_of)
  AND c.embedding_model_version = :current_model_version
ORDER BY distance ASC LIMIT 30;
```

**RRF (Reciprocal Rank Fusion, k=60) hợp nhất trong Python** (không phải SQL — dễ test, đúng quyết định gốc `phase-2.md`):

```python
def reciprocal_rank_fusion(bm25_ranked_ids: list[int], dense_ranked_ids: list[int], k: int = 60) -> dict[int, float]:
    scores: dict[int, float] = {}
    for rank, chunk_id in enumerate(bm25_ranked_ids, start=1):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1 / (k + rank)
    for rank, chunk_id in enumerate(dense_ranked_ids, start=1):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1 / (k + rank)
    return scores  # sắp giảm dần theo giá trị -> top-k tổng hợp
```

## 5. Viết lại câu hỏi (query rewrite) — Mức 2 đã chốt làm ngay

**Việc:** 1 lời gọi LLM nhỏ, prompt ngắn, mô hình cùng loại `deepseek-flash` (rẻ), TRƯỚC khi vào 2-C:

```json
// Prompt hệ thống (tóm tắt): "Viết lại câu hỏi thành 1 hoặc nhiều câu hỏi độc lập, đầy đủ ngữ cảnh,
// không suy diễn thông tin không có trong câu gốc. Sửa chính tả/viết tắt. Nếu câu hỏi chỉ có 1 ý, trả mảng 1 phần tử."
// Input: "ngày mai tôi đi làm mấy giờ ở hcm, mentor tôi là ai"
// Output:
{
  "standalone_questions": [
    "Giờ làm việc tại văn phòng Hồ Chí Minh là mấy giờ?",
    "Mentor cá nhân của nhân viên là ai?"
  ]
}
```

**Vì sao cần bước này** (không chỉ để tách ý): còn sửa cả các ca như:
- Viết tắt/không dấu: `"nghi phep nam may ngay"` → `"Nghỉ phép năm được bao nhiêu ngày?"` (đã có trong bộ câu hỏi V02 của `phase-2.md`).
- Câu hỏi phụ thuộc ngữ cảnh hội thoại trước đó (multi-turn, ví dụ "dùng hệ điều hành gì?" → "cài sao?") — **ghi chú:** xử lý đầy đủ hội thoại nhiều lượt vẫn là Phase 7 (cần lưu `conversations.context`), ở đây query rewrite chỉ xử lý được trong phạm vi 1 lượt hỏi hiện tại, chưa đọc lịch sử hội thoại trước.

**Chi phí/latency (đã nói ở lượt trước, nhắc lại cụ thể hơn):**
- Thêm đúng **1 lời gọi LLM** mỗi câu hỏi người dùng gửi (bất kể 1 ý hay nhiều ý) — không tránh được, vì không biết trước câu có mấy ý nếu không hỏi LLM.
- Ước tính: prompt rewrite ngắn (~200-400 token vào, ~100 token ra) → rẻ hơn nhiều so với lời gọi trả lời chính (evidence dài ~3.000 token).
- Latency cộng thêm: 1 round-trip LLM nữa trước khi bắt đầu tìm kiếm — đo thật ở 2-F.

## 6. `claims[]` — hợp đồng JSON mới của 2-D (Mức 1 đã chốt làm ngay)

Thay `{answer, quote, chunk_id}` bằng:

```json
{
  "claims": [
    {
      "question": "Giờ làm việc tại văn phòng Hồ Chí Minh là mấy giờ?",
      "response_type": "ANSWER",
      "text": "Giờ làm việc tại văn phòng Hồ Chí Minh là 8h30–17h30, thứ Hai đến thứ Sáu.",
      "quote": "Giờ làm việc tiêu chuẩn tại văn phòng Hồ Chí Minh là 8h30 đến 17h30...",
      "chunk_id": 12
    },
    {
      "question": "Mentor cá nhân của nhân viên là ai?",
      "response_type": "NO_BASIS",
      "reason_code": "out_of_scope",
      "text": null,
      "quote": null,
      "chunk_id": null
    }
  ]
}
```

**Validator (mở rộng từ bản gốc, lặp qua từng claim thay vì kiểm 1 lần):**
1. Với claim `response_type=ANSWER`: `quote` phải là chuỗi con nguyên văn của `content` một section đã đưa vào prompt (sau NFC + gộp khoảng trắng) — **giống hệt logic gốc**, chỉ chạy nhiều lần.
2. `chunk_id` phải thuộc tập chunk **của lượt tìm kiếm cho đúng câu hỏi con đó** (không được lấy `chunk_id` từ evidence của câu hỏi con khác — kiểm chặt theo từng `question`).
3. Claim nào không qua được kiểm tra → ép về `NO_BASIS` (không hiển thị answer chưa kiểm chứng), y như logic gốc.
4. `response_type=NO_BASIS` không cần `quote`/`chunk_id` — hợp lệ, không phải lỗi.

**Câu "mentor tôi là ai" luôn ra `NO_BASIS reason_code=out_of_scope`** dù retrieval có chạy tốt tới đâu — vì tài liệu HR không có thông tin này (đúng PRD), không phải giới hạn kỹ thuật.

## 7. Theo dõi từng bước bằng Langfuse

Đã có sẵn trong thiết kế gốc (`system-design.md`): **Langfuse là tùy chọn**, chỉ ghi **metadata** (không ghi nội dung câu hỏi/câu trả lời thật — che trước khi gửi), dùng để xem lại từng bước khi debug.

**Cấu hình** (`.env.example`, theo mẫu Ralion đã dùng thật):
```text
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=https://cloud.langfuse.com
LANGFUSE_ENABLED=false   # tắt mặc định; bật khi có khóa, không lỗi khi thiếu khóa
```

**Các bước được ghi thành 1 "trace" (1 trace = 1 câu hỏi người dùng gửi), mỗi bước là 1 "span":**

```text
Trace: "chat_ask" (trace_id = uuid mới mỗi lượt hỏi)
  ├─ span "rewrite_query"        input(đã che)=<hash>, output=<standalone_questions>, latency, token, cost
  ├─ span "retrieval" (x N câu con)
  │    ├─ span "bm25_search"     latency, số kết quả
  │    ├─ span "dense_search"    latency, số kết quả
  │    └─ span "rrf_merge"       số chunk sau hợp nhất, số section sau gộp cha
  ├─ span "llm_answer"           input(đã che)=<hash>, output=claims[], latency, token, cost, model
  └─ span "validate_claims"      số claim qua/không qua kiểm tra
```

**Che nội dung trước khi gửi Langfuse** (đúng nguyên tắc INV8 "không secret/dữ liệu nhạy cảm" đã có trong thiết kế): chỉ gửi **độ dài, số lượng, thời gian, chi phí, model, chunk_id** — không gửi nguyên văn câu hỏi hay câu trả lời. Muốn xem nội dung thật thì tra trực tiếp DB (`llm_call_logs` ở Phase 7) hoặc log cục bộ có kiểm soát, không phải qua Langfuse (dịch vụ ngoài).

**Không cần migration nào cho Langfuse** — đây là SDK gọi thẳng dịch vụ ngoài (Langfuse tự lưu trace phía họ), không phải bảng trong Postgres của VSF. Bảng `llm_call_logs` (lưu trong DB, dùng để tính chi phí tổng, không lưu nội dung) vẫn thuộc `0003_chat`, **để dành Phase 7** — không cần cho việc Langfuse hoạt động ở 2-D.

**Nếu chưa có khóa Langfuse:** `LANGFUSE_ENABLED=false`, mọi lời gọi tracing là no-op (không lỗi, không chặn). Đúng tinh thần "tùy chọn" đã ghi trong thiết kế.

## 8. Cây file (mở rộng từ `phase-2.md`)

```text
backend/src/services/retrieval/
    __init__.py
    hybrid_search.py       bm25_search(), dense_search(), reciprocal_rank_fusion(), search_and_merge_to_sections()

backend/src/services/chat/
    __init__.py
    query_rewrite.py       rewrite_query(question, llm) -> list[str]  (Mục 5)
    answer_service.py       answer_with_claims(questions, evidence, llm) -> list[Claim]  (Mục 6)
    validator.py            validate_claim(claim, retrieved_chunk_ids, section_content_by_id) -> Claim (ép NO_BASIS nếu sai)

backend/src/infrastructure/ai/
    chat_completion_port.py  ChatCompletionPort (Protocol) — adapter DeepSeek thật + FakeChatCompletion (test)

backend/src/infrastructure/observability/
    langfuse_tracer.py       LangfuseTracer (no-op khi LANGFUSE_ENABLED=false), mask_for_tracing()

backend/src/dto/response/chat_response_dto.py   ClaimResponseDTO, ChatAskResponseDTO
backend/src/dto/request/chat_request_dto.py     ChatAskRequestDTO {question, as_of?}
```

## 9. Ví dụ đầy đủ — câu hỏi 2 ý của bạn, chạy qua từng bước

**Input:** `"ngày mai tôi đi làm mấy giờ ở hcm, mentor tôi là ai"`

1. **rewrite_query** → `["Giờ làm việc tại văn phòng Hồ Chí Minh là mấy giờ?", "Mentor cá nhân của nhân viên là ai?"]`
2. **2-C chạy 2 lần** (1 lần/câu con):
   - Câu 1: BM25+dense tìm ra chunk về "giờ làm việc" (nếu có tài liệu — hiện `SYN_D03b` là chính sách nghỉ phép, **không có** mục giờ làm việc, nên thực tế với dữ liệu hiện có sẽ ra `NO_BASIS no_evidence`, không phải vì lỗi mà vì đúng là chưa nạp tài liệu đó).
   - Câu 2: BM25+dense tìm trên toàn bộ corpus — không tài liệu nào nói về "mentor cá nhân" (đúng, đây là dữ liệu cá nhân, không có trong chính sách) → không tìm ra evidence phù hợp.
3. **Evidence gộp lại:** có thể rỗng hoặc gần rỗng cho cả 2 câu con (vì dữ liệu hiện tại chỉ có 1 tài liệu về nghỉ phép).
4. **1 lời gọi LLM cuối** với evidence gần như rỗng → theo mục 2-D gốc: "khi truy xuất không có gì thì không gọi LLM, trả chưa có căn cứ ngay" — áp dụng cho từng claim độc lập.
5. **Kết quả trả về:**
   ```json
   {"claims": [
     {"question": "...giờ làm việc...", "response_type": "NO_BASIS", "reason_code": "no_evidence"},
     {"question": "...mentor...", "response_type": "NO_BASIS", "reason_code": "out_of_scope"}
   ]}
   ```

**Với dữ liệu thật hơn (nhiều tài liệu đã nạp ở Phase 5), câu 1 sẽ ra `ANSWER` thật nếu có tài liệu "giờ làm việc"; câu 2 vẫn luôn `NO_BASIS out_of_scope`.**

## 10. Kiểm chứng

| Việc | Cách kiểm |
|---|---|
| BM25/dense/RRF | Đơn vị: RRF thứ hạng, hòa điểm (thuần Python, không cần DB) |
| Lọc hiệu lực (`as_of`) | Tích hợp: version hết hạn/tương lai không được trả về |
| `rewrite_query` | Đơn vị với `FakeChatCompletion`: câu 1 ý → mảng 1 phần tử; câu 2 ý (ví dụ của bạn) → mảng 2 phần tử |
| `claims[]` + validator | Đơn vị: quote đúng/sai/thiếu 1 chữ cho từng claim độc lập; 1 claim đúng + 1 claim sai trong cùng response → chỉ claim sai bị ép `NO_BASIS`, claim đúng vẫn hiển thị |
| Langfuse | Đơn vị: `LANGFUSE_ENABLED=false` → no-op, không lỗi, không gọi mạng; có bật → kiểm nội dung gửi đi đã bị che (không chứa câu hỏi/câu trả lời nguyên văn) |
| Cú pháp BM25/vector thật | **Đã xong ở mục 2** — không cần spike lại |

## 11. Chi phí/latency tổng — so với bản gốc `phase-2.md` (chỉ 1 lời gọi LLM)

| | Bản gốc (`phase-2.md`) | Bản mở rộng (tài liệu này) |
|---|---|---|
| Số lời gọi LLM / câu hỏi | 1 | 2 (rewrite + answer), hoặc 3 nếu câu hỏi có 2 ý cần 2 lượt tìm kiếm riêng (tìm kiếm không phải LLM, chỉ tốn DB) |
| Số lượt truy vấn DB (BM25+dense) | 1 cặp | N cặp (N = số ý tách ra, thường 1, hiếm khi > 2) |
| Độ trễ thêm | — | + 1 round-trip LLM (rewrite), đo thật ở 2-F |
| Chi phí thêm | — | Nhỏ (prompt rewrite ngắn), đo thật ở 2-F |

## 12. Ba câu hỏi mở đã được bạn chốt

1. **Langfuse:** dùng chung tài khoản Ralion (đã chép `LANGFUSE_PUBLIC_KEY`/`SECRET_KEY`/`HOST` vào `.env`, `LANGFUSE_ENABLED=true`).
2. **Lưu trữ câu hỏi đã tách/viết lại:** **không lưu** — chỉ tồn tại trong bộ nhớ lúc xử lý 1 lượt hỏi (bảng `conversations`/`chat_messages` thuộc `0003_chat`, chưa tạo, để dành Phase 7). Chỗ duy nhất còn dấu vết là span Langfuse (đã che một phần, chỉ để debug, không phải nguồn tra cứu chính thức).
3. **Xử lý các câu hỏi con:** **song song** (`asyncio.gather`), không tuần tự — đã sửa ở mục 1 kiến trúc.

## 13. `lexical_text` của câu hỏi (khác với của tài liệu) — không lưu

- **Của tài liệu** (2-B, đã làm): lưu thật, cột `document_chunks.lexical_text`, tính 1 lần lúc nạp.
- **Của câu hỏi** (2-C, lúc tìm kiếm): **không lưu bảng nào** — tính tạm trong bộ nhớ bằng đúng hàm `to_lexical_text()` (tái dùng `src/services/ingest/lexical.py`, không viết hàm mới), dùng ngay trong câu `WHERE lexical_text @@@ :query_lexical`, dùng xong bỏ. Mỗi lượt hỏi một câu khác nhau, lưu lại không có giá trị tra cứu và không có bảng nào chứa (giống lý do ở mục 12.2).

Chốt xong — tôi bắt đầu code 2-C + 2-D mở rộng theo đúng cây file ở mục 8, xử lý song song các câu hỏi con.
