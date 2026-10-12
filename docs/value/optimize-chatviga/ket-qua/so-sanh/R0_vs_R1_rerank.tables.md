## Luồng C — tìm kiếm tài liệu (câu có đáp án)

| Chỉ số | R0_full | R1_full | Δ (test − base) | 95% CI của Δ | p (t cặp) | p (Wilcoxon) | Cohen d |
|---|---|---|---|---|---|---|---|
| Context Recall | 98.7% | 95.6% | -3.111 điểm % | [-6.930, +0.708] | 0.1088 | 0.1025 | -0.19 |
| Context Precision | 2.4% | 22.1% | +19.706 điểm % | [+17.098, +22.314] | 0.0000 | 0.0000 | +1.74 |
| Hit@1 | 53.3% | 82.4% | +29.111 điểm % | [+15.856, +42.366] | 0.0000 | 0.0002 | +0.51 |
| Hit@3 | 71.1% | 94.2% | +23.111 điểm % | [+12.948, +33.274] | 0.0000 | 0.0002 | +0.52 |
| Hit@5 | 75.6% | 95.6% | +20.000 điểm % | [+10.799, +29.201] | 0.0000 | 0.0002 | +0.50 |
| MRR | 0.646 | 0.878 | +0.232 | [+0.134, +0.329] | 0.0000 | 0.0001 | +0.55 |
| Phủ ý bắt buộc | 75.3% | 73.3% | -2.028 điểm % | [-9.992, +5.936] | 0.6133 | 0.5976 | -0.06 |
| Faithfulness (giám khảo) | 85.5% | 91.8% | +6.357 điểm % | [+0.639, +12.075] | 0.0298 | 0.0118 | +0.26 |
| Đúng 1-5 (giám khảo) | 4.507 | 4.473 | -0.033 | [-0.244, +0.178] | 0.7537 | 0.7263 | -0.04 |
| Đủ ý 1-5 | 4.113 | 4.027 | -0.087 | [-0.369, +0.196] | 0.5431 | 0.5378 | -0.07 |
| Liên quan 1-5 (Answer Relevancy) | 4.740 | 4.567 | -0.173 | [-0.365, +0.018] | 0.0753 | 0.1996 | -0.21 |
| Mạch lạc 1-5 | 3.473 | 3.413 | -0.060 | [-0.190, +0.070] | 0.3593 | 0.2005 | -0.11 |
| North Star: đúng và có căn cứ | 61.3% | 76.0% | +14.667 điểm % | [+2.890, +26.443] | 0.0154 | 0.0164 | +0.29 |
| Đúng loại phản hồi | 92.0% | 92.0% | +0.000 điểm % | [-7.565, +7.565] | 1.0000 | 1.0000 | +0.00 |
| Tỉ lệ lỗi | 1.3% | 1.3% | +0.000 điểm % | [+0.000, +0.000] | 1.0000 | nan | +0.00 |
| Số mục đưa vào LLM | 56.773 | 7.600 | -49.173 | [-56.946, -41.401] | 0.0000 | 0.0000 | -1.46 |
| Token ngữ cảnh | 4829.093 | 472.827 | -4356.267 | [-5011.560, -3700.973] | 0.0000 | 0.0000 | -1.53 |
| Token vào (cả câu) | 15652.013 | 5104.027 | -10547.987 | [-11896.144, -9199.829] | 0.0000 | 0.0000 | -1.80 |
| Chi phí LLM mỗi câu (USD) | 0.006 | 0.002 | -0.003 | [-0.004, -0.003] | 0.0000 | 0.0000 | -1.69 |

## Độ trễ và chi phí theo luồng (gộp mọi lượt, giây)

| Cấu hình | Luồng thực | n | P50 | P95 | P99 | Trung bình | Chi phí LLM/câu (USD) |
|---|---|---|---|---|---|---|---|
| R0_full | (tất cả — gộp, KHÔNG nên dùng làm số chính) | 120 | 5.32 | 9.89 | 12.01 | 4.98 | 0.00421 |
| R0_full | document | 85 | 5.75 | 10.26 | 14.47 | 6.61 | 0.00567 |
| R0_full | none | 1 | 6.75 | 6.75 | 6.75 | 6.75 | 0.00147 |
| R0_full | personal_guard | 6 | 0.02 | 0.04 | 0.05 | 0.03 | 0.00000 |
| R0_full | smalltalk | 11 | 1.16 | 1.25 | 1.29 | 1.11 | 0.00081 |
| R0_full | tool | 17 | 1.05 | 1.32 | 1.36 | 0.96 | 0.00072 |
| R1_full | (tất cả — gộp, KHÔNG nên dùng làm số chính) | 120 | 29.59 | 112.45 | 176.94 | 39.12 | 0.00178 |
| R1_full | document | 82 | 38.04 | 115.00 | 144.37 | 54.53 | 0.00230 |
| R1_full | none | 2 | 96.26 | 177.88 | 185.13 | 96.26 | 0.00126 |
| R1_full | personal_guard | 6 | 0.02 | 0.04 | 0.04 | 0.03 | 0.00000 |
| R1_full | smalltalk | 13 | 1.05 | 1.29 | 1.32 | 1.04 | 0.00081 |
| R1_full | tool | 17 | 1.09 | 1.38 | 1.58 | 0.99 | 0.00072 |

### Thời gian từng bước, luồng tài liệu có đáp án (giây, trung bình)

| Bước | R0_full | R1_full |
|---|---|---|
| router | 1.194 | 1.204 |
| rewrite | 1.143 | 1.065 |
| embed | 0.683 | 0.656 |
| truy_hồi | 0.178 | 94.306 |
| giây_rerank | 0.000 | 93.988 |
| trả_lời | 3.224 | 2.699 |
| kiểm_trích_dẫn | 0.000 | 0.000 |

## Luồng A — định tuyến ý định

| Nhóm (route kỳ vọng) | n/lượt | R0_full đúng | R1_full đúng |
|---|---|---|---|
| document | 83 | 96.4% | 92.8% |
| tool | 22 | 77.3% | 77.3% |
| out_of_scope | 5 | 0.0% | 0.0% |
| personal | 5 | 80.0% | 80.0% |
| injection | 3 | 0.0% | 0.0% |
| smalltalk | 2 | 100.0% | 100.0% |

Ma trận nhầm lẫn của R0_full (kỳ vọng → thực tế, tổng các lượt):

- `document` → `document`: 80
- `document` → `none`: 1
- `document` → `personal_guard`: 2
- `injection` → `smalltalk`: 3
- `out_of_scope` → `smalltalk`: 5
- `personal` → `personal_guard`: 4
- `personal` → `smalltalk`: 1
- `smalltalk` → `smalltalk`: 2
- `tool` → `document`: 5
- `tool` → `tool`: 17

## Luồng B — công cụ hành trình

| Chỉ số | R0_full | R1_full |
|---|---|---|
| Chọn đúng công cụ (câu đơn) | 68.8% | 68.8% |
| Đúng tham số ngày (get_day_plan) | 50.0% | 50.0% |
| Độ phủ các công cụ cần gọi (câu kép) | 58.3% | 58.3% |

## Theo nhóm câu hỏi (đúng loại phản hồi, lỗi, độ phủ ý)

| Nhóm | n | R0_full đúng loại | R1_full đúng loại | R0_full lỗi | R1_full lỗi |
|---|---|---|---|---|---|
| chèn lệnh | 3 | 0.0% | 0.0% | 0.0% | 0.0% |
| hành trình: câu kép nhiều công cụ | 6 | 83.3% | 66.7% | 0.0% | 0.0% |
| hành trình: công cụ | 16 | 50.0% | 56.2% | 0.0% | 0.0% |
| ngoài phạm vi | 5 | 0.0% | 0.0% | 0.0% | 0.0% |
| thông tin cá nhân | 5 | 80.0% | 80.0% | 0.0% | 0.0% |
| tài liệu: câu kép 2 ý | 17 | 100.0% | 100.0% | 0.0% | 0.0% |
| tài liệu: câu kép 3 ý | 8 | 87.5% | 75.0% | 12.5% | 12.5% |
| tài liệu: không có căn cứ | 8 | 75.0% | 75.0% | 0.0% | 12.5% |
| tài liệu: một sự kiện | 50 | 90.0% | 92.0% | 0.0% | 0.0% |
| xã giao | 2 | 100.0% | 100.0% | 0.0% | 0.0% |

## Đồng thuận giữa hai giám khảo (DeepSeek và gpt-5-mini, điểm 'Đúng')

```
{
 "n": 150,
 "spearman": 0.6366483747814811,
 "cohen_kappa_nhị_phân_(>=4)": 0.4134078212290503,
 "đồng_thuận_thô": 0.86,
 "chênh_>=2_điểm": 0.07333333333333333
}
```

## Bộ an toàn và độ bền

| Bộ | n | R0_safety: an toàn cơ học | R1_safety: an toàn cơ học | R0_safety: lỗi | R1_safety: lỗi | R0_safety: làm theo lệnh độc (giám khảo) |
|---|---|---|---|---|---|---|
| S1 chèn lệnh trực tiếp | 12 | 100.0% | 100.0% | 0.0% | 0.0% | 0.0% |
| S2 chèn lệnh gián tiếp (trong tài liệu) | 8 | 100.0% | 100.0% | 0.0% | 0.0% | 0.0% |
| S3 jailbreak và nội dung có hại | 3 | 100.0% | 100.0% | 0.0% | 0.0% | 0.0% |
| S4 lộ bí mật và thông tin cá nhân | 5 | 100.0% | 100.0% | 0.0% | 0.0% | 0.0% |
| S5 thiên lệch (cặp) | 6 | 100.0% | 100.0% | 0.0% | 0.0% | 0.0% |
| S6 độ bền (biến thể câu hỏi) | 9 | 100.0% | 100.0% | 0.0% | 0.0% | 0.0% |
| S7 câu mơ hồ | 3 | 100.0% | 100.0% | 0.0% | 0.0% | 0.0% |

Thiên lệch (3 cặp × 1 lượt): cùng loại phản hồi 100% ; độ giống từ trung bình giữa hai vế 0.88 (Jaccard).
