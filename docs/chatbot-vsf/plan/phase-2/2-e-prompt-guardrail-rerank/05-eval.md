# 2-E-6 — Eval: RAGAS triad thủ công cho golden set

> Phần 6/7. Xem [mục lục ở 2-e-1](00-tong-quan-doi-chieu.md). **Chưa code — chờ duyệt.**

`phase-2.md` mục 4 đã có kế hoạch bộ 10 câu hỏi golden set nhưng chưa gắn thước đo cụ thể. Bổ sung: chấm tay
theo đúng 3 trục RAGAS (slide `day08-rag-pipeline`), không cần cài thư viện `ragas` (thêm dependency, cần
ground-truth answer chuẩn hoá phức tạp hơn cần thiết cho 10 câu):

- **Context Recall**: với mỗi câu hỏi golden set, evidence trả về (`SectionEvidence[]`) có chứa đoạn chứa
  đáp án đúng không? (có/không, chấm tay vì đã biết trước tài liệu nguồn của từng câu).
- **Faithfulness**: **KHÔNG tự động hoá hoàn toàn được** — đính chính so với bản đầu (góp ý codex: nói
  "validator bảo đảm faithfulness" là nói quá). `validator.py` (INV13) chỉ chứng minh `claim.quote` là
  chuỗi NGUYÊN VĂN có thật trong tài liệu — đó là điều kiện cần, không phải đủ: `claim.text` (phần LLM
  diễn giải tự do) vẫn có thể suy diễn thêm ngoài những gì `quote` thực sự nói mà validator không bắt được
  (validator không so `text` với `content`, chỉ so `quote` với `content`). Tỷ lệ claim bị hạ NO_BASIS do
  quote sai chỉ đo được **một phần** của faithfulness (phần trích dẫn), dùng làm chỉ số phụ tham khảo —
  **vẫn phải đọc tay `claim.text` cho cả 10 câu golden set** để chấm faithfulness đầy đủ (text có đúng với
  nội dung claim.source hay đã suy diễn thêm), cùng lúc với việc chấm Answer Relevance.
- **Answer Relevance**: `claim.text` có trả lời đúng trọng tâm câu hỏi không? — chấm tay (1-5), vì cần đọc
  hiểu, không tự động hoá được với quy mô 10 câu.

Bảng chẩn đoán 3 trục thấp/cao → lớp cần sửa (Retrieval/Augmentation/Generation) dùng đúng bảng trong slide
day08, đưa vào `bao-cao-phase-2.md` khi chạy xong golden set:

| Recall | Faithfulness | Relevance | Chẩn đoán ưu tiên |
|---|---|---|---|
| Cao | Cao | Cao | Pipeline tốt |
| Thấp | Cao | Thấp | Sửa Retrieval — cân nhắc [rerank](01-retrieval-rerank.md) |
| Cao | Thấp | Cao | Sửa Generation (prompt/model) |
| Cao | Cao | Thấp | Sửa Augmentation (xem [2-e-3](02-augmentation.md)) |
| Thấp | Thấp | Thấp | Kiểm lại Indexing/dữ liệu gốc (2-B) |
