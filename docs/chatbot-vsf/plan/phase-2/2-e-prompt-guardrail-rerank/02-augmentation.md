# 2-E-3 — Augmentation: chuẩn hoá prompt structure

> Phần 3/7. Xem [mục lục ở 2-e-1](00-tong-quan-doi-chieu.md). **Chưa code — chờ duyệt.**

## 3.1 Tách System/Context/Question bằng delimiter rõ ràng

Hiện `answer_service._build_user_prompt` nối các đoạn context bằng `"\n\n"` thuần, không có tag phân vùng.
Theo slide (mục Augmentation·1): dùng tag/header rõ để model không lẫn dữ liệu với chỉ dẫn. Đổi sang:

```text
<context>
[Đoạn 1 — chunk_id=54 — nguồn: Quy định nghỉ phép — bản hiệu lực v3 — "Nghỉ phép năm"]
<nội dung đoạn>
[Đoạn 2 — ...]
</context>

<question id="1">Câu hỏi 1: ...</question>
<question id="2">Câu hỏi 2: ...</question>
```

`query_rewrite.py` cũng cần bọc câu hỏi thô của user trong tag `<user_input>` tương tự (xem chi tiết chống
injection ở [2-e-4](03-generation-guardrail-tien-kiem.md) mục 4.1).

## 3.2 Thứ tự chống "lost in the middle" — HOÃN, không bắt buộc trong đợt sửa này

> Sửa theo góp ý (codex): bản đầu coi "best-first-and-last" là việc nên làm ngay vì "sửa rẻ, không rủi
> ro" — nhận định đó chưa đúng. Với chỉ ~3-5 đoạn (`SECTION_TOKEN_BUDGET=3000`), đảo thứ tự là một thay
> đổi **có thể tốt lên hoặc xấu đi** tùy hành vi thật của DeepSeek trên context ngắn — chưa có số đo nào
> chứng minh chiều nào đúng, khác với 4.3 (giới hạn `standalone_questions[]`) là chặn rủi ro tốn tài
> nguyên rõ ràng bất kể model phản ứng thế nào.

Quyết định: **giữ nguyên thứ tự RRF hiện tại** (dễ kiểm chứng, dễ debug — đoạn #1 trong prompt luôn là đoạn
điểm cao nhất). Đưa việc này vào backlog cùng nhóm với rerank ([01-retrieval-rerank.md](01-retrieval-rerank.md)):
chỉ thử nghiệm reorder khi golden-set eval ([05-eval.md](05-eval.md)) cho thấy Answer Relevance thấp *trong khi*
Context Recall đã cao (tức đúng ca "Augmentation" theo bảng chẩn đoán RAGAS) — và khi đó so sánh A/B thứ tự
RRF gốc vs best-first-and-last trên chính golden set, không đổi mù.

## 3.3 Thêm metadata nguồn vào context đưa cho LLM

`_build_user_prompt` hiện chỉ đưa `heading`, không đưa `document_title`/`version_label` vào phần LLM nhìn
thấy — LLM không có cách phân biệt 2 đoạn cùng heading nhưng khác tài liệu. Thêm vào dòng tiêu đề mỗi đoạn:
`[Đoạn — chunk_id=... — {document_title} — bản {version_label} — {heading}]`.

## 3.4 Token budget tổng

`SECTION_TOKEN_BUDGET=3000` mới tính riêng phần context. Cần cộng thêm: system prompt (~300 token), câu hỏi
(thường <100 token/câu, tối đa vài câu con), output JSON dự kiến (~500 token cho vài claims) — tổng vẫn nằm
trong ngân sách an toàn của DeepSeek (context window lớn hơn nhiều so với 4000-5000 token cần). Không cần đổi
`SECTION_TOKEN_BUDGET`, chỉ ghi rõ phép tính này vào code comment để người sau không tăng bừa.
