# Kế hoạch bộ benchmark chuẩn cho chat Viga (bám slide AICB ngày 14 và ngày 18)

Ngày viết: 10/10/2026. Trạng thái: **kế hoạch, chờ bạn duyệt rồi mới chạy.** Chưa code, chưa gọi DeepSeek, chưa chạy phép đo nào trong tài liệu này. Các ngưỡng, công thức và quy trình dưới đây **trích từ slide** (`D:\AI_Action_lythuyet\slide\`): `day14-ai-evaluation-benchmarking.pdf` (Evaluation & Benchmarking), `2-day18-production-rag.pdf` (Production RAG), có đối chiếu `day13` (observability). Số đo hiện trạng của Viga lấy từ báo cáo 06/10/2026 (`docs/value/benchmark-modal-llm-viga/`). Bổ sung cho `ke-hoach-toi-uu-chat-viga.md` và `ke-hoach-benchmark-golden-set-reranker.md` trong cùng thư mục.

## 1. Mục tiêu và câu hỏi cần trả lời với mentor

Slide nhấn mạnh: *"Evaluation là engineering discipline, không phải cảm tính"* và mục tiêu cuối là *"biết agent tốt đến đâu, yếu ở đâu, và phải fix gì tiếp theo"*. Vì vậy báo cáo phải trả lời 4 câu:

1. **Viga hiện tốt đến đâu** theo 4 chỉ số RAG chuẩn và 4 chiều chất lượng (mục 4)?
2. **Yếu ở tầng nào** (router, rewrite, truy hồi, xếp hạng, ghép ngữ cảnh, sinh, kiểm trích dẫn)? (mục 7)
3. **Thêm reranker `bge-reranker-v2-m3` thì thay đổi gì**: độ chính xác truy hồi, độ chính xác câu trả lời, tốc độ, chi phí? (mục 8)
4. **Khác biệt đó có thật hay chỉ là nhiễu** (khoảng tin cậy, kiểm định thống kê)? (mục 6)

## 2. Nguyên tắc từ slide (và cách áp dụng cho Viga)

| Nguyên tắc (slide) | Áp dụng |
|---|---|
| Thiết kế thí nghiệm: **giả thuyết → chạy benchmark → đo → kết luận**, lặp lại được, so sánh được, tự động hóa được (ngày 14, slide 8) | Mỗi phương án có giả thuyết viết trước; ghi phiên bản mã, bộ dữ liệu, mô hình; chạy bằng một lệnh |
| Chỉ kết luận **"v2 tốt hơn"** khi: chạy ≥ 3 lần, báo cáo mean ± std hoặc CI, kiểm định cặp p < 0,05, đủ mẫu (tính power), kiểm guardrails, tách theo category/difficulty, effect size > 0,05 (slide 58) | Checklist cuối báo cáo (mục 6) |
| **Fix retriever trước, generator sau**: Context Recall → Context Precision → Faithfulness → Answer Relevancy (ngày 14, slide 49) | Thứ tự phân tích lỗi ở mục 7 |
| *"Đừng đổi model, vặn đúng tầng"*; chẩn đoán trước, sửa sau; Error Tree (ngày 18) | Mỗi thay đổi trong thí nghiệm gắn với một tầng cụ thể |
| So sánh **A Naive / B Production / C Tự chọn**, cùng dữ liệu, cùng judge (ngày 18, slide 49) | Cấu hình A/B/C ở mục 8 |
| Chọn **1 North Star + 2–3 Guardrail + Diagnostic** (ngày 14, slide 22) | Mục 4 |

## 2b. Tách ba luồng đo riêng (không gộp chung)

Viga có ba đường xử lý với tính chất rất khác nhau, nên **mỗi đường có bộ câu, metric, độ trễ và báo cáo riêng**; không lấy trung bình gộp:

| Luồng | Việc xảy ra | Tốc độ điển hình | Metric chính |
|---|---|---|---|
| **A. Định tuyến ý định (intent routing)** | Guard regex → shortcut regex → router LLM (ngưỡng 0,55) → quyết định nhánh | Guard/shortcut không gọi LLM; router khoảng 1,1 giây | Độ chính xác định tuyến, ma trận nhầm lẫn, precision/recall từng nhánh, độ trễ định tuyến |
| **B. Công cụ hành trình (tool, gọi dữ liệu trong DB)** | `get_next_tasks`, `get_day_plan`, `explain_lock`, `get_task_detail`, `get_progress` chạy xác định | Rất nhanh (không LLM ở bước thực thi) | Tool selection accuracy, parameter accuracy, tính đúng của kết quả, độ trễ công cụ (slide 60) |
| **C. Tìm kiếm tài liệu (RAG: rewrite, truy hồi hybrid, rerank, sinh, kiểm trích dẫn)** | Pipeline tài liệu | Chậm nhất: khoảng 4–6 giây, p95 khoảng 10 giây | 4 chỉ số RAG, 4 chiều chất lượng, độ trễ từng bước, rerank |

**Vì sao phải tách:**
- Công cụ hành trình nhanh và không có truy hồi, nên gộp vào cùng trung bình làm **độ trễ trông tốt giả** và **Context Recall/Precision loãng** (câu tool không có ngữ cảnh để tính).
- Một câu có thể sai vì **định tuyến sai** (bị đẩy nhầm sang tool hoặc sang tài liệu) chứ không phải vì truy hồi kém; nếu không tách thì lỗi định tuyến bị tính vào truy hồi và ngược lại.

**Cách đo để cô lập từng luồng:**
1. **Luồng A (định tuyến):** mỗi câu có nhãn `expected_route` (hành trình/tool nào, tài liệu, ngoài phạm vi, thông tin cá nhân, trò chuyện xã giao). Chỉ chạy tầng định tuyến (không chạy phần trả lời) và so với nhãn. Báo: accuracy, **ma trận nhầm lẫn**, precision/recall từng nhánh, tỉ lệ **rơi về tài liệu do độ tin cậy < 0,55**, độ trễ định tuyến (tách luật regex và router LLM), và lỗi đã biết (câu thời tiết bị luật "hôm nay" bắt).
2. **Luồng C (tài liệu):** chạy **ép định tuyến về tài liệu** (bỏ qua router) trên các câu có nhãn tài liệu, để Recall/Precision/Faithfulness phản ánh đúng phần **truy hồi + rerank + sinh** chứ không lẫn lỗi định tuyến. Đây là luồng chạy thí nghiệm **R0 và R1 (rerank)**.
3. **Luồng B (tool):** so tên công cụ và tham số với nhãn (`tool`, `params`), so kết quả công cụ với trạng thái hành trình mong đợi (trạng thái task, khóa/mở, thứ tự); không có metric RAG.
4. **Đo toàn tuyến (end-to-end)** là một phần phụ, chạy cả ba luồng như người dùng thật; báo **riêng từng luồng** (P50/P95 độ trễ, chính xác) kèm **tỉ trọng lưu lượng** của từng luồng nếu muốn một con số tổng, và ghi rõ tỉ trọng đó chọn theo dữ liệu dev (chưa phản ánh lưu lượng thật).

**Báo cáo độ trễ:** chia theo luồng: shortcut/guard (không LLM), tool (một lần router + công cụ), tài liệu (đủ các bước). Mục tiêu P95 ≤ 5 giây của slide áp dụng **cho luồng tài liệu** là chỗ đang vượt (10,67 giây gộp); luồng tool/shortcut dự kiến đã dưới ngưỡng và phải chứng minh bằng số đo riêng.

## 3. Bộ dữ liệu chuẩn (golden dataset)

Theo slide 24–32 (ngày 14):

- **Quy mô (đã chốt theo yêu cầu): khoảng 100 câu, chỉ gồm câu đơn và câu kép**, không có hội thoại nhiều lượt. Slide khuyến nghị 50–100 cặp cho mức sản xuất (20 chỉ là bài lab).
  - **Câu đơn (khoảng 60):** một ý, một đáp án; gồm cả các ca biên đứng riêng: không có căn cứ, ngoài phạm vi, thông tin cá nhân, chèn lệnh, viết tắt/sai chính tả.
  - **Câu kép (khoảng 40):** hai đến ba ý trong một câu ("VNeID, CMND và Teams thì sao?"), phải trả lời đủ từng ý và nói rõ ý nào chưa có căn cứ; đây là ca Viga từng mất ý khi tắt thinking nên cần đủ mẫu.
  - **Phân bổ theo luồng (đề xuất, cần bạn xác nhận):** khoảng **65 câu cho luồng tài liệu C** (đơn và kép, nơi đo hybrid + rerank), khoảng **25 câu cho luồng hành trình/tool B** (đơn và kép, ví dụ "việc tiếp theo và vì sao task kia bị khóa?"), khoảng **10 câu chỉ để kiểm định tuyến A** (ngoài phạm vi, cá nhân, xã giao, câu bẫy giống tool nhưng là tài liệu và ngược lại). Mọi câu đều có `expected_route`, nên luồng A dùng chung toàn bộ 100 câu. Nếu muốn so rerank chắc chắn hơn thì tăng phần C, giảm phần B.
  - **Chia: 70 câu phát triển + 30 câu đóng băng** (giữ tỉ lệ đơn/kép và tỉ lệ theo luồng ở cả hai phần). Đủ cho kiểm định cặp (power analysis: phát hiện chênh 0,05 với độ lệch 0,1 cần khoảng 31 câu); nhưng **chỉ 30 câu đóng băng nên kiểm cuối chỉ là xác nhận, không đủ để phát hiện chênh nhỏ**, và phân tích theo từng nhóm con sẽ có khoảng tin cậy rộng.
  - Hệ quả của việc bỏ nhiều lượt: bộ này **không đo** khả năng hiểu "câu hỏi tiếp theo" và bước viết lại theo lịch sử; báo cáo phải ghi rõ đây là phạm vi chưa đo.
- **Lược đồ mỗi mục (theo slide 26, thêm trường cho Viga):** `id, question, expected_route (document / tool:<tên> / out_of_scope / personal / smalltalk), expected_tool + expected_params (cho luồng tool), reference_answer, contexts_expected (id mục tài liệu), quote_expected, category, difficulty (easy/medium/hard), tags, persona, as_of, expected_response_type, must_include[], must_not[], created_by, reviewed_by, version, created_at`.
- **Phân tầng (stratified sampling):** mỗi ô (category × difficulty) có đủ mẫu; câu thường gặp không lấn át câu hiếm.
- **Edge cases bắt buộc (slide 29–30), trong phạm vi câu đơn và câu kép:** mơ hồ, ngoài phạm vi, **đối kháng ≥ 10% (≥ 10 trong 100 câu)** (chèn lệnh, đóng vai, đòi dữ liệu cá nhân, sai chính tả/viết tắt, trộn Việt–Anh), câu kép nhiều ý/nhiều tài liệu, theo ngày hiệu lực (`as_of`). Hỏi tiếp nhiều lượt: **không đưa vào bộ này**.
- **Cách tạo (slide 25, kết hợp):** LLM sinh bản nháp từ từng mục tài liệu (cách 3) → thêm câu thật từ log/phản hồi 👎 (cách 2) → chuyên gia viết tay ca khó và ca đối kháng (cách 1).
- **Kiểm nhãn:** *"LLM-generated without review = benchmark rác"*: **100% câu qua mắt người**; **mỗi đáp án do ít nhất 2 người duyệt**; tính **Cohen's κ** giữa hai người; **κ < 0,6 thì không dùng bộ này, phải sửa rubric** (slide 28). Mọi trích dẫn chuẩn kiểm cơ học bằng `text_match.quote_matches` (phải nằm nguyên văn trong tài liệu).
- **Chống nhiễm dữ liệu (slide 31):** bộ riêng tư, có mã băm và phiên bản trong Git, thêm chuỗi canary; bộ 30 câu đóng băng chỉ dùng kiểm cuối.
- **Tiến hóa:** mỗi vòng thêm các ca thất bại vào bộ (vòng cải tiến liên tục, slide 71).

## 4. Metric chính xác (định nghĩa, công thức, ngưỡng, cách đo cho Viga)

### 4.1 Bốn chiều chất lượng đầu ra (slide 9)
Correctness, Completeness, Relevance, Coherence: mỗi chiều chấm 1–5 theo rubric có ví dụ cho từng mức.

### 4.2 Bốn chỉ số RAG (slide 18–20, 42, 48)

| Chỉ số | Công thức (slide) | Ngưỡng slide | Cách đo ở Viga |
|---|---|---|---|
| **Context Recall** | số ý của đáp án chuẩn có trong ngữ cảnh ÷ tổng số ý của đáp án chuẩn | ≥ 0,75 (production), ≥ 0,8 là tốt | Ý chuẩn = `must_include` + `contexts_expected`; kiểm mục chuẩn có nằm trong ngữ cảnh đưa vào LLM không (**sau khi cắt 3.000 token**, và **sau rerank nếu có**) |
| **Context Precision** | trung bình có trọng số vị trí: (1/K) Σ (số mục liên quan trong top-k ÷ k) · 1[mục k liên quan] | ≥ 0,75 | "Liên quan" = mục nằm trong `contexts_expected` hoặc chứa trích dẫn chuẩn; tính trên top-K của ngữ cảnh |
| **Faithfulness** | số claim trong câu trả lời được ngữ cảnh đỡ ÷ tổng claim | ≥ 0,85 (sản xuất), < 0,7 = chặn deploy | Viga đã tách claim sẵn (`claims` + trích nguyên văn). Tính **hai lớp**: (a) cơ học: tỉ lệ claim có trích dẫn nguyên văn đúng mục (`validator`); (b) giám khảo LLM: claim có được ngữ cảnh đỡ về ý nghĩa không |
| **Answer Relevancy** | trung bình cosine(emb(câu hỏi gốc), emb(câu hỏi sinh ngược từ câu trả lời)) | ≥ 0,80 | DeepSeek sinh n câu hỏi ngược; embedding bằng BGE-M3 (máy embedding local) |

Slide cảnh báo: *Faithfulness không đo đúng sự thật, chỉ đo "bám ngữ cảnh"*; ngữ cảnh sai (tài liệu cũ) vẫn cho Faithfulness cao → cần thêm câu theo `as_of` và câu mâu thuẫn phiên bản (slide 19, 39 ngày 18). RAGAS **kém tin cậy với tiếng Việt, đa lượt, domain chuyên biệt** (slide 51) → bắt buộc kết hợp giám khảo tùy chỉnh và người chấm mẫu.

### 4.3 Chấm tổng hợp bằng giám khảo (LLM-as-Judge, slide 33–43)
- Thang 1–5 theo rubric có ví dụ từng mức (mẫu slide 36); kèm **lý do** (rationale); **chain-of-thought** (slide 39: tăng đồng thuận với người 15–20%); **nhiệt độ = 0** (slide 41).
- Dùng **tham chiếu** (reference-based) cho câu có đáp án chuẩn; **không tham chiếu** (reference-free) cho coherence/safety (slide 37).
- Với so sánh A/B nên có **pairwise** (đảo vị trí A/B, lấy trung bình) để giảm thiên lệch (slide 38).
- **7 loại thiên lệch** cần kiểm: vị trí, độ dài, tự ưa (cùng họ mô hình), a dua, thẩm quyền, định dạng, gần cuối (slide 40). Biện pháp tương ứng ghi trong rubric và cách trộn thứ tự.
- **Hiệu chỉnh với người (slide 42):** 50+ câu, 2 chuyên gia chấm (κ giữa hai người ≥ 0,6), giám khảo chấm lại cùng 50 câu; chấp nhận khi **Spearman ρ ≥ 0,7 hoặc κ ≥ 0,6**; nếu thấp: sửa rubric, thêm ví dụ, đổi mô hình giám khảo, thêm CoT, hoặc dùng nhiều giám khảo. Lặp lại mỗi 3 tháng hoặc khi đổi mô hình giám khảo.
- **Đã chốt (10/10/2026): hai giám khảo khác họ.** Giám khảo 1 = DeepSeek (khóa của dự án này); **giám khảo 2 = OpenAI `gpt-5-mini`** (rẻ, khác họ), dùng khóa `OPENAI_API_KEY` của dự án P-040 do bạn cho phép. Đã gọi thử một lệnh nhỏ: dùng được, còn hạn mức. Khóa chỉ đọc lúc chạy từ `P-040/.env`, **không sao chép vào repo này, không commit**; chỉ gửi sang OpenAI nội dung benchmark (tài liệu mẫu giả lập và câu trả lời), không có dữ liệu người dùng thật. `gpt-5-nano` rẻ hơn nữa sẽ được thử ở bước hiệu chỉnh nếu cần giảm chi phí. Groq (Qwen) là họ thứ ba nếu muốn ensemble 3 giám khảo. Gemini trong P-040 bị từ chối (401).
- **Rào chắn của chúng ta:** chỉ có khóa DeepSeek → giám khảo **cùng họ** với mô hình trả lời (nguy cơ tự ưa). Giảm bằng: (1) chấm **cơ học trước** (loại phản hồi, trích dẫn nguyên văn, ý bắt buộc, chuỗi cấm); (2) hiệu chỉnh với người như trên; (3) ghi rõ hạn chế trong báo cáo. **Nếu bạn có thêm khóa của một hãng khác (Claude, OpenAI, Gemini)** thì thêm một giám khảo thứ hai để chạy ensemble 2 giám khảo, đánh dấu câu chênh ≥ 2 điểm để người xem lại (slide 43).

### 4.4 Chỉ số kinh doanh và vận hành (slide 21–22)

| Chỉ số | Mục tiêu (slide) | Hiện trạng Viga (đã đo 06/10/2026) |
|---|---|---|
| **P95 độ trễ** | ≤ 5 giây | **10,67 giây** (chưa đạt); p50 5,95 giây |
| Chi phí mỗi câu | ≤ 0,05 USD | ≈ 0,003 USD (đạt rất xa) |
| Tỉ lệ giải quyết (resolution) | ≥ 70% | Chưa đo; đo offline bằng "đúng + bám nguồn + không phải chuyển HR" |
| Thumbs-up | ≥ 60% | Dữ liệu 👍👎 có nhưng chưa lên báo cáo; dữ liệu dev quá ít |
| Tỉ lệ từ chối | ≤ 5% | Tính trên câu **có thể trả lời** (câu không có căn cứ từ chối là đúng) |

**Khung 3 lớp (slide 22):** *North Star* của benchmark offline = **tỉ lệ "trả lời đúng và có căn cứ"** (điểm giám khảo ≥ 4 **và** Faithfulness ≥ 0,85 **và** trích dẫn hợp lệ, trên câu có thể trả lời) cộng tỉ lệ từ chối đúng ở câu không có căn cứ. *Guardrail:* P95 độ trễ, Faithfulness ≥ 0,85, tỉ lệ từ chối sai ≤ 5%, 0 bịa thông tin cá nhân. *Diagnostic:* 4 chỉ số RAG, theo category/difficulty, theo tầng. Mọi cải tiến phải tăng North Star mà không phá Guardrail; nếu đánh đổi thì là quyết định kinh doanh, không phải kỹ thuật (slide 22).

### 4.5 An toàn và đối kháng (slide 62–63)
Mục tiêu từ slide: jailbreak ≥ 95% từ chối; chèn lệnh ≥ 99% phát hiện; rò PII 0%; nội dung độc hại 0%; lời khuyên tài chính/y tế 100% từ chối hoặc nêu miễn trừ. Với Viga: câu chèn lệnh, đòi lương/người hướng dẫn/chỗ ngồi (phải từ chối + gợi ý gửi HR), đòi email/số điện thoại không có trong danh bạ (không được bịa), thử lộ system prompt.

### 4.6 Tiêu chí độ trễ và chi phí (slide ngày 13, 14 và 18)

Slide coi độ trễ và chi phí là **guardrail**: mọi cải tiến về chất lượng không được phá chúng; ngược lại tối ưu tốc độ không được làm tụt chất lượng. Mỗi tiêu chí được đo **riêng cho từng luồng A/B/C** (mục 2b) và **riêng cho từng bước** trong luồng C.

| Tiêu chí | Ngưỡng / quy tắc (slide) | Hiện trạng Viga (đã đo 06/10/2026) | Cách đo trong benchmark |
|---|---|---|---|
| **Độ trễ P50 / P95 / P99** | P95 ≤ 5 giây (ngày 14 và cảnh báo ngày 13); ví dụ điển hình P50 ≈ 2,5 s, P95 ≈ 5 s, P99 ≈ 8 s+. *Trung bình ẩn đuôi dài; P95 mới là trải nghiệm thật* | P50 5,95 s, **P95 10,67 s (chưa đạt)**; P99 chưa đo; số này là **gộp** cả luồng tool và tài liệu | Phân vị P50/P95/P99 **riêng từng luồng** và từng bước (route, rewrite, embed, truy hồi, rerank, trả lời, kiểm trích dẫn); P99 của **cả pipeline** chứ không chỉ từng lệnh (slide 23: đuôi cộng dồn ở workflow nhiều bước) |
| **TTFT (thời gian tới token đầu)** | Ví dụ điển hình 2026: P50 ≈ 0,5–1,0 s, P95 ≈ 1,5–2,5 s (cho trải nghiệm "nhanh") | **Chưa đo**: Viga không stream | Đo ở chế độ stream trong harness cho bước trả lời; tách **prefill (đọc ngữ cảnh)** và **suy luận** |
| **Chế độ suy luận (thinking) là lớp độ trễ riêng** | Slide: chậm hơn 5–30 lần, *tách ra khi đo* | Thinking bật ở bước trả lời: ~460/621 token ra là suy luận ẩn | Báo cáo hai nhóm riêng: thinking bật và tắt, không trộn chung |
| **Thông lượng, hàng đợi** | Throughput (req/s, token/s); saturation (hàng đợi, rate-limit) | `LlmGate` 9 lệnh đồng thời, tài khoản 11 yêu cầu đồng thời; `queue_wait_ms` có trong `llm_calls` | Chạy thêm một lượt tải nhẹ (ví dụ 5 và 10 người hỏi cùng lúc) để xem độ trễ P95 và `queue_wait_ms`; không so với hạn mức production |
| **Token vào / ra (tách riêng)** | Output đắt gấp 5–6 lần input nên phải tách (slide 24) | Vào ~7.500 / ra ~620 ở bước trả lời | Từ `llm_calls` (`prompt_tokens`, `completion_tokens`, `reasoning_tokens`, `cached_input_tokens`) |
| **Chi phí mỗi câu / mỗi tác vụ** | ≤ 0,05 USD mỗi truy vấn (ngày 14). *Cost-per-task ≠ cost-per-LLM-call*: một câu có thể gọi nhiều lần (route, rewrite, trả lời, thử lại, giám khảo không tính) | ≈ 0,003 USD (rất đạt) | Cộng chi phí **mọi lệnh LLM của một câu** theo `request_id`, báo theo luồng và theo cấu hình |
| **Chi phí mỗi câu được giải quyết đúng** (cost per resolved query) | Chỉ số kinh doanh bắt buộc (ngày 14, slide 21) | Chưa đo | Tổng chi phí chia cho số câu đạt "đúng + bám nguồn"; **cách công bằng để so R0 và R1** vì rerank có thể tăng chi phí nhưng tăng số câu đúng |
| **Chi phí hạ tầng của reranker** | Open-weight không tính phí giấy phép nhưng tốn compute (slide ngày 18) | Chưa có | Giây CPU mỗi câu × giá giờ máy (ước theo loại máy sẽ chạy) cộng vào chi phí mỗi câu; **ghi riêng** để thấy rerank có thu hồi được bằng việc ngữ cảnh ngắn đi (ít token vào) hay không |
| **Tỉ lệ cache** | Cache hit rate là chỉ số theo dõi (ngày 13) | `cached_input_tokens` ghi trong `llm_calls`; sản phẩm chưa có cache câu hỏi | Báo tỉ lệ token đầu vào được cache khi đặt phần cố định ở đầu prompt |
| **Tỉ lệ lỗi** | Cảnh báo khi > 5%; uptime ≥ 99% (slide 73) | Chưa đo riêng | Tỉ lệ lỗi/timeout/429 mỗi cấu hình, phân loại theo `error_type` |
| **SLI/SLO** | SLI = số đo (ví dụ % câu < 5 s), SLO = mục tiêu (ví dụ 95% câu < 5 s); *không có hậu quả rõ ràng thì là SLO chứ không phải SLA* | Chưa định nghĩa | Đề xuất SLI "% câu luồng tài liệu < 5 s" và "% câu luồng tool < 2 s" (ngưỡng luồng tool là đề xuất của tôi, slide không quy định) |

**Quy tắc đo để số có ý nghĩa:**
- Chạy các cấu hình **xen kẽ** trong cùng khoảng thời gian (mạng và tải DeepSeek thay đổi); ≥ 3 lượt mỗi cấu hình; báo P50/P95 kèm khoảng tin cậy (bootstrap hoặc phân vị trên các lượt).
- Lượt đầu tiên của mỗi tiến trình có thể chậm vì khởi động lạnh (embedding, mô hình rerank): **bỏ các lệnh khởi động lạnh khỏi phân vị** nhưng báo riêng số lần xảy ra.
- Độ trễ rerank đo **hai nơi**: máy dev và ước cho máy 2 vCPU trên AWS (chưa đo ở đó); không suy ra số production từ số máy dev.
- Quy tắc cổng: một cấu hình chỉ được gọi là "tốt hơn" khi **chất lượng không giảm vượt nhiễu** *và* **độ trễ P95 và chi phí không xấu đi quá 5%** so với đối chứng (slide 57 ngày 14, phần A/B: guardrail cost/latency/error không xấu hơn 5%), hoặc phải ghi rõ đây là đánh đổi để người quyết định kinh doanh chọn (slide 22).
- Báo cáo thêm biểu đồ **thác nước theo bước** (phần nào trong tổng thời gian) cho từng luồng, và đường ngưỡng SLO vẽ lên mọi biểu đồ độ trễ (slide ngày 13 về lỗi dashboard hay gặp: không có đường baseline/ngưỡng).

## 5. Quy trình chạy (có thể lặp lại)

1. **Khóa phiên bản:** ghi mã băm commit, phiên bản golden set, mô hình trả lời (`deepseek-flash`, tham số), mô hình embedding và `embedding_model_version`, phiên bản reranker, checksum kho tài liệu, mô hình giám khảo và prompt giám khảo.
2. **Nạp kho tài liệu** (`day1`, `core`) vào **DB tạm riêng**, không đụng DB dev/production.
3. **Chạy từng cấu hình trên toàn bộ golden set**, ghi mỗi câu: câu con sau rewrite, mục truy hồi (id, hạng BM25, hạng vector, điểm RRF, điểm rerank), ngữ cảnh thực đưa vào LLM, câu trả lời, claim và trích dẫn, kết quả validator, có thử lại không, **thời gian từng bước** và token (nối `llm_calls` bằng `request_id`).
4. **Chạy ≥ 3 lần mỗi cấu hình** (slide 58), giữ tham số sinh mặc định của sản phẩm (không đặt temperature) để phản ánh sản phẩm thật; thêm một lần chạy kiểm chứng nhiệt độ thấp để tách nhiễu sinh khỏi nhiễu hệ thống.
5. **Chấm:** cơ học → 4 chỉ số RAG → giám khảo 1–5 (4 chiều) → an toàn.
6. **Phân tích:** kiểm định, khoảng tin cậy, phân tích theo tầng và theo category/difficulty, gom nhóm thất bại.
7. **Báo cáo:** theo blueprint slide 76 (mục 9).

## 6. Thống kê (để báo cáo với mentor có cơ sở)

- Mỗi số báo cáo ở dạng **trung bình ± độ lệch chuẩn (hoặc khoảng tin cậy 95%)**; ví dụ CI = x̄ ± 1,96·s/√n (n ≥ 30), dùng phân phối t khi n nhỏ (slide 53–54).
- So hai cấu hình trên **cùng bộ câu**: **kiểm định t cặp (`scipy.stats.ttest_rel`)**, kết luận khi **p < 0,05** (slide 55); thêm kiểm định không tham số (Wilcoxon) cho điểm 1–5 vì không chuẩn.
- **Power analysis (slide 56):** n ≈ (z_α + z_β)²·σ² ÷ Δ²; với Δ = 0,05, σ = 0,1, α = 0,05, 80% power thì n ≈ 31; bộ 100 câu (70 phát triển) đủ cho so sánh tổng thể, nhưng **các nhóm con (câu kép khoảng 40, ca biên vài chục) có thể dưới 31 câu**, nên kết luận theo nhóm con chỉ mang tính gợi ý. Tính lại σ thật sau lượt chạy đầu.
- **Effect size** > 0,05 mới coi là có ý nghĩa nghiệp vụ; tách theo category/difficulty để thấy cấu hình tốt hơn ở **mọi** phân khúc hay chỉ một nhóm (slide 58).
- **Checklist trước khi nói "tốt hơn":** ≥ 3 lần chạy · mean ± std/CI · p < 0,05 · đủ mẫu · guardrails không xấu đi (độ trễ, chi phí, lỗi) · tách theo phân khúc · effect size đủ lớn.
- Với phương án rẻ về hạ tầng nhưng chậm hơn thì báo cả hai chiều (đánh đổi chính xác – độ trễ).

## 7. Tìm nguyên nhân: đo gì ở từng tầng

Slide dạy chẩn đoán theo bản đồ pipeline (Parse → Chunk → Enrich → Embed → Index → PreRAG → Retrieve → Rerank → Augment → Generate → PostRAG) và Error Tree. Với Viga, tôi gắn mỗi chỉ số vào đúng tầng để một câu sai có thể truy về nguyên nhân:

| Tầng của Viga | Chỉ số / phép đo | Nếu thấp thì nghĩa là |
|---|---|---|
| **Luồng A:** Guard + Shortcut + Router | Độ chính xác định tuyến (đúng nhánh: tool nào / tài liệu / ngoài phạm vi / cá nhân), ma trận nhầm lẫn, precision/recall từng nhánh, tỉ lệ rơi về tài liệu vì độ tin cậy < 0,55; **đo riêng, không gộp với truy hồi** | Luật regex hoặc router sai (ví dụ câu thời tiết bị bắt bởi "hôm nay …") |
| **Luồng B:** công cụ hành trình | Tool selection accuracy, parameter accuracy, kết quả đúng trạng thái hành trình; độ trễ công cụ | Công cụ chọn sai hoặc dữ liệu hành trình diễn giải sai |
| Rewrite + tách câu con | Tỉ lệ ý bắt buộc được phủ bởi các câu con; tỉ lệ câu bị viết lại sai nghĩa | Mất ý ở bước tách |
| Truy hồi BM25 / vector / RRF | **Recall@k và MRR riêng cho BM25, vector và RRF** (tách để biết nguồn nào thiếu) | Từ vựng lệch (cần HyDE/đa truy vấn), phân từ tiếng Việt, kho chưa index đúng |
| Ghép ngữ cảnh (cắt 3.000 token) | Tỉ lệ mục chuẩn **bị cắt** dù đã truy hồi được; số token ngữ cảnh | Ngân sách token cắt mất mục đúng |
| **Rerank** (thí nghiệm) | NDCG@k, MRR, Precision@k trước/sau; mục chuẩn có lên top không | Bộ xếp hạng chưa đủ tinh |
| Sinh | Faithfulness, Answer Relevancy, Completeness; tỉ lệ bịa | Prompt, mô hình, thinking |
| Validator | **Tỉ lệ từ chối sai**: câu trả lời đúng nhưng trích dẫn bị từ chối (đối chiếu với giám khảo) và tỉ lệ thử lại | Quy tắc khớp nguyên văn quá chặt với mục dài |
| Toàn tuyến | Độ trễ từng bước, token ngữ cảnh ↔ thời gian tới token đầu, chi phí | Chỗ nghẽn |

**Phân loại thất bại (slide 67) và quy trình (slide 68–70):** mỗi câu sai được gán một loại — *Wrong Answer, Hallucination, Retrieval miss, Rerank drop, Context truncation, Validator false-reject, Wrong route, Refusal sai, Personal fabrication, Slow, Inconsistent* — viết theo **mẫu nhật ký thất bại** (case_id, câu hỏi, kỳ vọng, thực tế, loại lỗi, giả thuyết gốc, bằng chứng gồm mục truy hồi so với mục kỳ vọng, ưu tiên, kế hoạch sửa). **Gom nhóm theo nguyên nhân gốc** (không sửa lẻ từng câu), **5 Whys** cho 3 ca tệ nhất, ưu tiên nhóm lớn nhất. Slide ví dụ: nếu 80% lỗi là truy hồi thì sửa truy hồi lợi hơn sửa prompt.

**Thứ tự chẩn đoán (slide 49, 43):** Context Recall thấp → hybrid/HyDE/multi-query/đổi cách cắt; Context Precision thấp → **rerank**, ngưỡng điểm, lọc metadata; Faithfulness thấp → prompt chặt, giảm nhiệt độ, trích dẫn; Answer Relevancy thấp → prompt/khuôn trả lời. Sửa **rẻ trước đắt sau**: recall → precision → faithfulness.

## 8. Thí nghiệm rerank và các biến thay đổi

**Reranker được chọn: `bge-reranker-v2-m3`** (đúng khuyến nghị slide ngày 18: *"Tiếng Việt + self-host → bge-reranker-v2-m3"*, tiếng Việt tốt, 8K context). Cần **xác nhận giấy phép trên thẻ mô hình** trước khi dùng thương mại (chưa kiểm). Slide nêu mức tham khảo: thêm khoảng 30–50 ms mỗi truy vấn trên GPU/CPU mạnh để tăng khoảng 15–25% precision (tùy dữ liệu); **đây là số của slide, chưa phải số của Viga**: phải đo trên máy thật của chúng ta (CPU 2 nhân).

**Thiết kế hai cấu hình chính (theo mẫu A/B/C của slide 49):**

| Cấu hình | Truy hồi | Số mục đưa vào LLM | Rerank | Ghi chú |
|---|---|---|---|---|
| **R0 (hiện tại)** | BM25 + vector, RRF k=60 | theo ngân sách 3.000 token mỗi câu con | Không | Đối chứng (không đổi sản phẩm) |
| **R1 (có rerank)** | Giống R0, lấy **top 20** | **top 3–5** sau rerank (theo slide, top-20 → top-3) | `bge-reranker-v2-m3` | Cắt ngữ cảnh mạnh |

**Giả thuyết cần kiểm (viết trước khi chạy):**
1. Context Precision tăng (có thể ≥ +0,10), Context Recall không đổi hoặc giảm nhẹ nếu cắt còn top 3 (reranker không thể tìm thêm mục không có trong top 20; slide: *"vô dụng nếu chunk đúng chưa được retrieve"*).
2. Số token ngữ cảnh giảm từ khoảng 7.500 xuống khoảng một phần ba, nên **bước LLM trả lời nhanh hơn**; câu hỏi chính là bù trừ giữa thời gian rerank cộng thêm và thời gian tiết kiệm ở bước trả lời.
3. Faithfulness và tỉ lệ trích dẫn qua validator ngay lần đầu **không xấu đi**, vì ngữ cảnh sạch hơn.
4. Độ chính xác câu trả lời tổng không giảm (cổng chất lượng ở mục 6).

**Các biến đổi thêm để tìm nguyên nhân (mỗi lần chỉ đổi MỘT biến so với R0 hoặc R1, rồi mới gộp):**

| Biến | Giá trị thử | Tầng bị tác động | Chỉ số kỳ vọng đổi |
|---|---|---|---|
| Reranker | không / `bge-reranker-v2-m3` | Rerank | Precision, MRR, token ngữ cảnh |
| Số mục sau rerank | 3 / 5 / 8 | Ghép ngữ cảnh | Recall (giảm khi ít mục), độ trễ trả lời |
| Ngưỡng điểm rerank | không / ngưỡng chọn từ golden set | Rerank | Từ chối sai, Precision |
| Thinking ở bước trả lời | bật / tắt | Sinh | Độ trễ, Completeness câu nhiều ý |
| Ngữ cảnh người dùng trong prompt | không / thẻ tiến độ ngắn | Sinh, rewrite | Độ nhạy theo người, Relevancy câu cá nhân |
| Ưu tiên theo task đang mở | không / có | Truy hồi | Recall ở câu "việc của tôi" |

Ngoài ra, **mỗi cấu hình sẽ đo thêm**: Recall@5/10/20 của riêng BM25, của riêng vector và của RRF, để xem reranker đang sửa lỗi xếp hạng hay chỉ che lỗi truy hồi.

**Lưu ý máy chạy reranker:** đo độ trễ trên **máy dev** (bản chạy thử) và ước tính cho **máy embedding 2 vCPU trên AWS** (chưa đo; cần đo thật nếu định triển khai). Độ trễ rerank phụ thuộc số cặp (20 cặp mỗi câu con × tối đa 5 câu con).

## 9. Đầu ra báo cáo (theo blueprint slide 76)

1. Golden dataset (phiên bản, mã băm, thống kê phân tầng, κ giữa hai người duyệt).
2. Điểm 4 chỉ số RAG + 4 chiều chất lượng cho từng cấu hình, **mean ± std/CI**, theo category/difficulty.
3. Kết quả giám khảo LLM (và đối chiếu người: Spearman/κ).
4. So sánh R0 vs R1 và từng biến đổi: bảng delta, p-value, effect size, độ trễ từng bước, chi phí.
5. Phân tích 3 ca tệ nhất (5 Whys) và gom nhóm nguyên nhân gốc.
6. **Nhật ký cải tiến:** tối thiểu 3 hành động ưu tiên theo tác động, kèm tầng và chi phí.
7. Nhận định hiện trạng chat Viga: đạt/không đạt từng ngưỡng của slide.

## 10. Chi phí và nguồn lực (ước tính, chưa đo)

Theo slide 13: 20 câu × 4 chỉ số × giám khảo ≈ 80 lệnh gọi, khoảng 1–4 USD mỗi lần chạy với mô hình lớn. Với DeepSeek flash rẻ hơn nhiều: ước tính **cả đợt thí nghiệm chính (R0 và R1, 100 câu, 3 lần, đủ chỉ số)** khoảng vài USD đến vài chục USD tùy số lệnh giám khảo mỗi câu; mỗi biến đổi thêm tăng một phần. Con số chính xác chỉ có sau khi chạy thử 10 câu.
Nhân lực: **2 người duyệt nhãn** (bạn và một người nữa như mentor/HR; ước khoảng 3 giờ mỗi người cho 100 câu) và 50 câu chấm tay để hiệu chỉnh giám khảo.

## 11. Rủi ro và hạn chế

- Dữ liệu tổng hợp; persona dev chỉ khác ở team và hành trình.
- Giám khảo cùng họ DeepSeek: có thể thiên lệch (slide 40: self-preference); đã giảm nhưng không loại bỏ.
- RAGAS/giám khảo yếu hơn với tiếng Việt và đa lượt (slide 51): các câu đa lượt chấm bằng quy tắc cơ học và người nhiều hơn.
- Kết quả độ trễ phụ thuộc mạng và tải DeepSeek; phải chạy các cấu hình **xen kẽ** trong cùng khoảng thời gian.
- Giấy phép `bge-reranker-v2-m3` chưa xác nhận; chưa đo độ trễ trên máy AWS 2 vCPU.
- Số liệu từ slide (49%, 67%, +15–25% precision, 30–50 ms) là tham khảo của giáo trình, không phải kết quả của Viga.

## 12. Cần bạn quyết trước khi chạy

1. **Người duyệt nhãn thứ hai** (mentor/HR?) và thời điểm; nếu chưa có thì chỉ một người duyệt và báo cáo ghi rõ chưa đạt chuẩn κ của slide.
2. **Có khóa của hãng LLM khác** để làm giám khảo thứ hai không (khuyến nghị theo slide); nếu không thì dùng DeepSeek hai cấu hình giám khảo và ghi hạn chế.
3. **Chi phí:** đồng ý chạy thử 10 câu trước để tính chi phí thật rồi quyết chạy toàn bộ.
4. **Rerank:** đồng ý dùng `bge-reranker-v2-m3` chạy cục bộ trong harness (cài thư viện trong môi trường thử, không đụng sản phẩm).
5. **Phạm vi lượt đầu:** chỉ **R0 so với R1** (như bạn nói), các biến đổi còn lại làm sau khi có kết quả đầu.
