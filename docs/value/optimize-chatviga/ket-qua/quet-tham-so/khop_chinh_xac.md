Đo truy hồi trên 10 câu cần khớp đúng chuỗi (không LLM). Số trong bảng đầu là HẠNG của mục đúng (— = ngoài top 30).

| Câu | BM25 riêng | vector riêng | RRF mặc định (k=60, 1:1) | RRF tối ưu (k=10, 0,1:1) | RRF k=10, 0,5:1 | tối ưu + giữ chỗ BM25 |
|---|---|---|---|---|---|---|
| em_01 Form IT-SW-01 dùng để làm gì? | 1 | 1 | 1 | 1 | 1 | 1 |
| em_02 FAC-02 là form gì vậy? | 1 | 1 | 1 | 1 | 1 | 1 |
| em_03 IT-DEV-01 để yêu cầu việc gì? | 1 | 1 | 1 | 1 | 1 | 1 |
| em_04 Khi nào thì gửi mail cho soc-oncall@vsf-demo.example | 1 | 1 | 1 | 1 | 1 | 1 |
| em_05 facilities@vsf-demo.example là liên hệ về việc gì? | 1 | 1 | 1 | 1 | 1 | 1 |
| em_06 Chương trình đào tạo hội nhập liên hệ v.thudq@vinsma | 1 | 1 | 1 | 1 | 1 | 1 |
| em_07 WAF, ZTNA, PAM là gì và ai quyết định có dùng không? | 1 | 1 | 1 | 1 | 1 | 1 |
| em_08 it.vsf-demo.example/software-catalog là trang gì? | 1 | 1 | 1 | 1 | 1 | 1 |
| em_09 Security request form to VINSOC nằm ở đâu? | 1 | 1 | 1 | 1 | 1 | 1 |
| em_10 support.vinsmartfuture.tech/app/vinithelpdesk dùng đ | 1 | 1 | 1 | 1 | 1 | 1 |
| em_11 IT-ACC-01 | 1 | 2 | 1 | 1 | 1 | 1 |
| em_12 FAC-01 | 1 | 2 | 1 | 1 | 1 | 1 |
| em_13 ZTNA | 1 | 1 | 1 | 1 | 1 | 1 |
| em_14 VINSOC | 2 | 2 | 2 | 2 | 2 | 2 |
| em_15 soc-oncall | 1 | 1 | 1 | 1 | 1 | 1 |
| em_16 OSlq7VPRkk | 1 | 5 | 1 | 4 | 1 | 4 |
| em_17 hr.vsf-demo.example | 1 | 2 | 1 | 1 | 1 | 1 |
| em_18 PTVH | 1 | 1 | 1 | 1 | 1 | 1 |

| Cách xếp hạng | Hit@1 | Hit@3 | Hit@5 |
|---|---|---|---|
| BM25 riêng | 94% | 100% | 100% |
| vector riêng | 72% | 94% | 100% |
| RRF mặc định (k=60, 1:1) | 94% | 100% | 100% |
| RRF tối ưu (k=10, 0,1:1) | 89% | 94% | 100% |
| RRF k=10, 0,5:1 | 94% | 100% | 100% |
| tối ưu + giữ chỗ BM25 | 89% | 94% | 100% |
