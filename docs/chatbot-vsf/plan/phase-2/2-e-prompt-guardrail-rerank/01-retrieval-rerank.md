# 2-E-2 — Rerank: quyết định KHÔNG thêm cho MVP

> Phần 2/7. Xem [mục lục ở 2-e-1](00-tong-quan-doi-chieu.md). **Chưa code — chờ duyệt.**

Slide `day08-rag-pipeline` mô tả rerank là "search rộng (top-20), chấm kỹ bằng cross-encoder (rerank), chọn
top-3-5" — tăng độ chính xác nhưng thêm latency + chi phí (ví dụ trong slide: +5% relevance, 1s→4s latency,
chi phí gấp đôi). Bài tự luận 5 của slide đúng tình huống này, kết luận: "Không có đáp án tuyệt đối — cân
nhắc theo SLO, mức độ nghiêm trọng, có thể route thích ứng (chỉ câu khó mới qua reranker)".

## Đã có quyết định D5 từ trước — không phải đề xuất mới

`P-040\docs\PlaningForOptimize\srs\chatbot-vsf\vsf-onboarding-assistant-system-design.md` (dòng 231, bảng
quyết định D5 dòng 548) đã chốt sẵn: **"Reranker: chưa dùng ở MVP (lab không chứng minh lợi ích, tốn độ
trễ); bật `bge-reranker-v2-m3` khi đo thấy Recall@5 chưa đạt."** Tài liệu này không đổi quyết định đó —
chỉ nhắc lại và nối vào quy trình đo cụ thể ([05-eval.md](05-eval.md)) để biết chính xác khi nào "đo thấy
cần" là đủ điều kiện bật.

## Áp cho VSF (lý do bổ sung, cùng chiều với D5)

Corpus hiện tại nhỏ (vài chục tài liệu HR/onboarding, không phải hàng chục nghìn), `BM25_TOP_K=DENSE_TOP_K=30`
đã là tập nhỏ, RRF đã hợp lý hoá thứ hạng giữa 2 nguồn. Đây là **giả thuyết chưa đo**, không phải bằng chứng —
đúng góp ý (codex): không nên coi "corpus nhỏ nên rerank không giúp gì" là kết luận chắc chắn. Cross-encoder
rerank luôn cộng thêm latency (mỗi câu hỏi con gọi thêm 1 model) và một dependency mới — cái giá này là chắc
chắn, còn lợi ích thì chưa đo nên chưa biết.

## Quyết định (giữ nguyên, đã xác nhận lại với bạn)

Không code rerank thật trong đợt sửa này — đúng quyết định D5 cũ. Việc cần làm ngay: tạo
`retrieval/rerank.py` dạng **passthrough** (xem [07-cay-thu-muc-code.md](07-cay-thu-muc-code.md)) làm chỗ
cắm sẵn, để khi golden-set eval ([05-eval.md](05-eval.md)) cho kết quả Recall@5 không đạt (Context Recall
thấp, Faithfulness cao — đúng lỗi Retrieval theo bảng chẩn đoán RAGAS) thì chỉ cần điền `bge-reranker-v2-m3`
vào file có sẵn, không phải sửa lại `hybrid_search.py`/`search_to_sections`.
