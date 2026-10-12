Quét rerank trên 49 câu (tập chỉnh). Nền: RRF k=10, BM25:vector=0.1:1. Thời gian đo ở máy dev với dịch vụ rerank hiện chạy.

| Cấu hình | Hit@1 | Hit@3 | Hit@5 | MRR | Recall@5 | giây/cặp | giây/câu hỏi |
|---|---|---|---|---|---|---|---|
| chỉ RRF (không rerank), 20 ứng viên | 55.4% | 79.9% | 87.4% | 0.687 | 87.4% |  |  |
| chỉ RRF (không rerank), 12 ứng viên | 55.4% | 79.9% | 87.4% | 0.686 | 87.4% |  |  |
| rerank lexical_512, 20 ứng viên | 68.7% | 87.4% | 92.2% | 0.784 | 92.2% | 1.15 | 22.99 |
| rerank lexical_512, 12 ứng viên | 70.7% | 87.4% | 92.2% | 0.793 | 92.2% | 1.15 | 13.79 |
| rerank natural_512, 20 ứng viên | 66.7% | 87.4% | 93.2% | 0.773 | 93.2% | 1.14 | 22.9 |
| rerank natural_512, 12 ứng viên | 68.7% | 87.4% | 92.2% | 0.781 | 92.2% | 1.14 | 13.74 |
| rerank natural_256, 20 ứng viên | 66.7% | 87.4% | 93.2% | 0.775 | 93.2% | 0.89 | 17.84 |
| rerank natural_256, 12 ứng viên | 68.7% | 87.4% | 92.2% | 0.783 | 92.2% | 0.89 | 10.7 |
