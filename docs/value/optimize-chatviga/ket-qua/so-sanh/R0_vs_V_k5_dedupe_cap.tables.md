## Luồng C — tìm kiếm tài liệu (câu có đáp án)

| Chỉ số | R0_full | V_k5_dedupe_cap | Δ (test − base) | 95% CI của Δ | p (t cặp) | p (Wilcoxon) | Cohen d |
|---|---|---|---|---|---|---|---|
| Context Recall | 98.7% | 76.0% | -22.667 điểm % | [-32.385, -12.948] | 0.0000 | 0.0001 | -0.54 |
| Context Precision | 2.4% | 15.6% | +13.162 điểm % | [+10.787, +15.537] | 0.0000 | 0.0000 | +1.28 |
| Hit@1 | 53.3% | 54.4% | +1.111 điểm % | [-2.361, +4.583] | 0.5257 | 0.5930 | +0.07 |
| Hit@3 | 71.1% | 71.6% | +0.444 điểm % | [-2.768, +3.657] | 0.7836 | 0.6547 | +0.03 |
| Hit@5 | 75.6% | 76.0% | +0.444 điểm % | [-2.768, +3.657] | 0.7836 | 0.6547 | +0.03 |
| MRR | 0.646 | 0.634 | -0.012 | [-0.047, +0.022] | 0.4837 | 0.0090 | -0.08 |
| Phủ ý bắt buộc | 75.3% | 63.2% | -12.124 điểm % | [-21.881, -2.367] | 0.0156 | 0.0116 | -0.29 |
| Faithfulness (giám khảo) | 85.5% | 91.5% | +5.989 điểm % | [-0.638, +12.617] | 0.0758 | 0.0451 | +0.21 |
| Đúng 1-5 (giám khảo) | 4.507 | 4.147 | -0.360 | [-0.631, -0.089] | 0.0100 | 0.0157 | -0.31 |
| Đủ ý 1-5 | 4.113 | 3.587 | -0.527 | [-0.875, -0.178] | 0.0036 | 0.0043 | -0.35 |
| Liên quan 1-5 (Answer Relevancy) | 4.740 | 4.240 | -0.500 | [-0.780, -0.220] | 0.0007 | 0.0007 | -0.41 |
| Mạch lạc 1-5 | 3.473 | 3.393 | -0.080 | [-0.233, +0.073] | 0.2994 | 0.1578 | -0.12 |
| North Star: đúng và có căn cứ | 61.3% | 58.7% | -2.667 điểm % | [-16.806, +11.473] | 0.7081 | 0.7055 | -0.04 |
| Đúng loại phản hồi | 92.0% | 86.7% | -5.333 điểm % | [-12.797, +2.130] | 0.1587 | 0.1573 | -0.16 |
| Tỉ lệ lỗi | 1.3% | 0.0% | -1.333 điểm % | [-3.990, +1.323] | 0.3206 | 0.3173 | -0.12 |
| Số mục đưa vào LLM | 56.773 | 7.533 | -49.240 | [-57.062, -41.418] | 0.0000 | 0.0000 | -1.45 |
| Token ngữ cảnh | 4829.093 | 571.613 | -4257.480 | [-4905.390, -3609.570] | 0.0000 | 0.0000 | -1.51 |
| Token vào (cả câu) | 15652.013 | 5305.040 | -10346.973 | [-11704.229, -8989.718] | 0.0000 | 0.0000 | -1.75 |
| Chi phí LLM mỗi câu (USD) | 0.006 | 0.003 | -0.003 | [-0.004, -0.003] | 0.0000 | 0.0000 | -1.42 |

## Độ trễ và chi phí theo luồng (gộp mọi lượt, giây)

| Cấu hình | Luồng thực | n | P50 | P95 | P99 | Trung bình | Chi phí LLM/câu (USD) |
|---|---|---|---|---|---|---|---|
| R0_full | (tất cả — gộp, KHÔNG nên dùng làm số chính) | 120 | 5.32 | 9.89 | 12.01 | 4.98 | 0.00421 |
| R0_full | document | 85 | 5.75 | 10.26 | 14.47 | 6.61 | 0.00567 |
| R0_full | none | 1 | 6.75 | 6.75 | 6.75 | 6.75 | 0.00147 |
| R0_full | personal_guard | 6 | 0.02 | 0.04 | 0.05 | 0.03 | 0.00000 |
| R0_full | smalltalk | 11 | 1.16 | 1.25 | 1.29 | 1.11 | 0.00081 |
| R0_full | tool | 17 | 1.05 | 1.32 | 1.36 | 0.96 | 0.00072 |
| V_k5_dedupe_cap | (tất cả — gộp, KHÔNG nên dùng làm số chính) | 120 | 5.06 | 10.97 | 17.90 | 4.92 | 0.00198 |
| V_k5_dedupe_cap | document | 85 | 5.57 | 11.86 | 19.22 | 6.61 | 0.00253 |
| V_k5_dedupe_cap | personal_guard | 6 | 0.02 | 0.03 | 0.03 | 0.02 | 0.00000 |
| V_k5_dedupe_cap | smalltalk | 12 | 1.08 | 1.26 | 1.30 | 1.06 | 0.00081 |
| V_k5_dedupe_cap | tool | 17 | 1.08 | 1.21 | 1.24 | 0.95 | 0.00072 |

### Thời gian từng bước, luồng tài liệu có đáp án (giây, trung bình)

| Bước | R0_full | V_k5_dedupe_cap |
|---|---|---|
| router | 1.194 | 1.380 |
| rewrite | 1.143 | 1.175 |
| embed | 0.683 | 0.650 |
| truy_hồi | 0.178 | 0.095 |
| giây_rerank | 0.000 | 0.000 |
| trả_lời | 3.224 | 3.369 |
| kiểm_trích_dẫn | 0.000 | 0.000 |

## Luồng A — định tuyến ý định

| Nhóm (route kỳ vọng) | n/lượt | R0_full đúng | V_k5_dedupe_cap đúng |
|---|---|---|---|
| document | 83 | 96.4% | 96.4% |
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

| Chỉ số | R0_full | V_k5_dedupe_cap |
|---|---|---|
| Chọn đúng công cụ (câu đơn) | 68.8% | 68.8% |
| Đúng tham số ngày (get_day_plan) | 50.0% | 50.0% |
| Độ phủ các công cụ cần gọi (câu kép) | 58.3% | 58.3% |

## Theo nhóm câu hỏi (đúng loại phản hồi, lỗi, độ phủ ý)

| Nhóm | n | R0_full đúng loại | V_k5_dedupe_cap đúng loại | R0_full lỗi | V_k5_dedupe_cap lỗi |
|---|---|---|---|---|---|
| chèn lệnh | 3 | 0.0% | 0.0% | 0.0% | 0.0% |
| hành trình: câu kép nhiều công cụ | 6 | 83.3% | 83.3% | 0.0% | 0.0% |
| hành trình: công cụ | 16 | 50.0% | 56.2% | 0.0% | 0.0% |
| ngoài phạm vi | 5 | 0.0% | 0.0% | 0.0% | 0.0% |
| thông tin cá nhân | 5 | 80.0% | 80.0% | 0.0% | 0.0% |
| tài liệu: câu kép 2 ý | 17 | 100.0% | 100.0% | 0.0% | 0.0% |
| tài liệu: câu kép 3 ý | 8 | 87.5% | 87.5% | 12.5% | 0.0% |
| tài liệu: không có căn cứ | 8 | 75.0% | 75.0% | 0.0% | 0.0% |
| tài liệu: một sự kiện | 50 | 90.0% | 82.0% | 0.0% | 0.0% |
| xã giao | 2 | 100.0% | 100.0% | 0.0% | 0.0% |

## Đồng thuận giữa hai giám khảo (DeepSeek và gpt-5-mini, điểm 'Đúng')

```
{
 "n": 150,
 "spearman": 0.7247538585760028,
 "cohen_kappa_nhị_phân_(>=4)": 0.48575949367088617,
 "đồng_thuận_thô": 0.8266666666666667,
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
