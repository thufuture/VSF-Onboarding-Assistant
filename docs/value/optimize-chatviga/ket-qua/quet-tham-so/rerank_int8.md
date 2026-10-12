Quét rerank trên 49 câu (tập chỉnh). Nền: RRF k=10, BM25:vector=0.1:1. Thời gian đo ở máy dev với dịch vụ rerank hiện chạy.

| Cấu hình | Hit@1 | Hit@3 | Hit@5 | MRR | Recall@5 | giây/cặp | giây/câu hỏi |
|---|---|---|---|---|---|---|---|
| chỉ RRF (không rerank), 12 ứng viên | 55.4% | 79.9% | 87.4% | 0.686 | 87.4% |  |  |
| rerank natural_256, 12 ứng viên | 68.7% | 87.4% | 92.2% | 0.787 | 92.2% | 0.37 | 4.39 |
| rerank lexical_256, 12 ứng viên | 70.7% | 87.4% | 92.2% | 0.798 | 92.2% | 0.37 | 4.44 |
