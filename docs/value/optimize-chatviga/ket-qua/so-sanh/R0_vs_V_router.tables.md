## Luồng C — tìm kiếm tài liệu (câu có đáp án)

| Chỉ số | R0_full | V_router | Δ (test − base) | 95% CI của Δ | p (t cặp) | p (Wilcoxon) | Cohen d |
|---|---|---|---|---|---|---|---|
| Context Recall | 98.7% | 98.7% | +0.000 điểm % | [-3.782, +3.782] | 1.0000 | 1.0000 | +0.00 |
| Context Precision | 2.4% | 2.5% | +0.119 điểm % | [-0.066, +0.304] | 0.2038 | 0.2143 | +0.15 |
| Hit@1 | 53.3% | 54.7% | +1.333 điểm % | [-1.323, +3.990] | 0.3206 | 0.3173 | +0.12 |
| Hit@3 | 71.1% | 71.8% | +0.667 điểm % | [-2.320, +3.653] | 0.6578 | 0.6547 | +0.05 |
| Hit@5 | 75.6% | 76.2% | +0.667 điểm % | [-2.320, +3.653] | 0.6578 | 0.6547 | +0.05 |
| MRR | 0.646 | 0.656 | +0.011 | [-0.017, +0.038] | 0.4523 | 0.2475 | +0.09 |
| Phủ ý bắt buộc | 75.3% | 75.6% | +0.333 điểm % | [-3.830, +4.496] | 0.8737 | 0.9313 | +0.02 |
| Faithfulness (giám khảo) | 85.5% | 88.5% | +2.976 điểm % | [-2.685, +8.637] | 0.2983 | 0.2580 | +0.12 |
| Đúng 1-5 (giám khảo) | 4.507 | 4.527 | +0.020 | [-0.151, +0.191] | 0.8160 | 0.8551 | +0.03 |
| Đủ ý 1-5 | 4.113 | 4.040 | -0.073 | [-0.271, +0.125] | 0.4630 | 0.3142 | -0.09 |
| Liên quan 1-5 (Answer Relevancy) | 4.740 | 4.760 | +0.020 | [-0.117, +0.157] | 0.7719 | 0.8763 | +0.03 |
| Mạch lạc 1-5 | 3.473 | 3.500 | +0.027 | [-0.078, +0.132] | 0.6147 | 0.5684 | +0.06 |
| North Star: đúng và có căn cứ | 61.3% | 62.7% | +1.333 điểm % | [-10.919, +13.586] | 0.8289 | 0.8273 | +0.03 |
| Đúng loại phản hồi | 92.0% | 93.3% | +1.333 điểm % | [-3.289, +5.956] | 0.5672 | 0.5637 | +0.07 |
| Tỉ lệ lỗi | 1.3% | 0.0% | -1.333 điểm % | [-3.990, +1.323] | 0.3206 | 0.3173 | -0.12 |
| Số mục đưa vào LLM | 56.773 | 54.480 | -2.293 | [-8.421, +3.834] | 0.4582 | 0.2998 | -0.09 |
| Token ngữ cảnh | 4829.093 | 4481.760 | -347.333 | [-847.782, +153.116] | 0.1709 | 0.0794 | -0.16 |
| Token vào (cả câu) | 15652.013 | 16434.813 | +782.800 | [-443.905, +2009.505] | 0.2075 | 0.0000 | +0.15 |
| Chi phí LLM mỗi câu (USD) | 0.006 | 0.006 | +0.000 | [-0.000, +0.001] | 0.1733 | 0.0001 | +0.16 |

## Độ trễ và chi phí theo luồng (gộp mọi lượt, giây)

| Cấu hình | Luồng thực | n | P50 | P95 | P99 | Trung bình | Chi phí LLM/câu (USD) |
|---|---|---|---|---|---|---|---|
| R0_full | (tất cả — gộp, KHÔNG nên dùng làm số chính) | 120 | 5.32 | 9.89 | 12.01 | 4.98 | 0.00421 |
| R0_full | document | 85 | 5.75 | 10.26 | 14.47 | 6.61 | 0.00567 |
| R0_full | none | 1 | 6.75 | 6.75 | 6.75 | 6.75 | 0.00147 |
| R0_full | personal_guard | 6 | 0.02 | 0.04 | 0.05 | 0.03 | 0.00000 |
| R0_full | smalltalk | 11 | 1.16 | 1.25 | 1.29 | 1.11 | 0.00081 |
| R0_full | tool | 17 | 1.05 | 1.32 | 1.36 | 0.96 | 0.00072 |
| V_router | (tất cả — gộp, KHÔNG nên dùng làm số chính) | 120 | 4.77 | 12.14 | 20.63 | 5.13 | 0.00457 |
| V_router | document | 86 | 5.30 | 13.21 | 24.70 | 6.82 | 0.00610 |
| V_router | none | 10 | 1.07 | 1.37 | 1.42 | 1.10 | 0.00093 |
| V_router | personal_guard | 6 | 0.02 | 0.04 | 0.04 | 0.02 | 0.00000 |
| V_router | smalltalk | 2 | 1.02 | 1.07 | 1.07 | 1.02 | 0.00092 |
| V_router | tool | 16 | 1.02 | 1.41 | 1.47 | 0.97 | 0.00081 |

### Thời gian từng bước, luồng tài liệu có đáp án (giây, trung bình)

| Bước | R0_full | V_router |
|---|---|---|
| router | 1.194 | 1.108 |
| rewrite | 1.143 | 1.021 |
| embed | 0.683 | 0.645 |
| truy_hồi | 0.178 | 0.102 |
| giây_rerank | 0.000 | 0.000 |
| trả_lời | 3.224 | 3.322 |
| kiểm_trích_dẫn | 0.000 | 0.000 |

## Luồng A — định tuyến ý định

| Nhóm (route kỳ vọng) | n/lượt | R0_full đúng | V_router đúng |
|---|---|---|---|
| document | 83 | 96.4% | 96.4% |
| tool | 22 | 77.3% | 72.7% |
| out_of_scope | 5 | 0.0% | 100.0% |
| personal | 5 | 80.0% | 100.0% |
| injection | 3 | 0.0% | 100.0% |
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

| Chỉ số | R0_full | V_router |
|---|---|---|
| Chọn đúng công cụ (câu đơn) | 68.8% | 75.0% |
| Đúng tham số ngày (get_day_plan) | 50.0% | 50.0% |
| Độ phủ các công cụ cần gọi (câu kép) | 58.3% | 33.3% |

## Theo nhóm câu hỏi (đúng loại phản hồi, lỗi, độ phủ ý)

| Nhóm | n | R0_full đúng loại | V_router đúng loại | R0_full lỗi | V_router lỗi |
|---|---|---|---|---|---|
| chèn lệnh | 3 | 0.0% | 100.0% | 0.0% | 0.0% |
| hành trình: câu kép nhiều công cụ | 6 | 83.3% | 66.7% | 0.0% | 0.0% |
| hành trình: công cụ | 16 | 50.0% | 50.0% | 0.0% | 0.0% |
| ngoài phạm vi | 5 | 0.0% | 100.0% | 0.0% | 0.0% |
| thông tin cá nhân | 5 | 80.0% | 100.0% | 0.0% | 0.0% |
| tài liệu: câu kép 2 ý | 17 | 100.0% | 94.1% | 0.0% | 0.0% |
| tài liệu: câu kép 3 ý | 8 | 87.5% | 100.0% | 12.5% | 0.0% |
| tài liệu: không có căn cứ | 8 | 75.0% | 62.5% | 0.0% | 0.0% |
| tài liệu: một sự kiện | 50 | 90.0% | 92.0% | 0.0% | 0.0% |
| xã giao | 2 | 100.0% | 100.0% | 0.0% | 0.0% |

## Đồng thuận giữa hai giám khảo (DeepSeek và gpt-5-mini, điểm 'Đúng')

```
{
 "n": 150,
 "spearman": 0.48310932984066096,
 "cohen_kappa_nhị_phân_(>=4)": 0.40722619495671786,
 "đồng_thuận_thô": 0.86,
 "chênh_>=2_điểm": 0.07333333333333333
}
```

## Bộ an toàn và độ bền

| Bộ | n | R0_safety: an toàn cơ học | V_router_safety: an toàn cơ học | R0_safety: lỗi | V_router_safety: lỗi | R0_safety: làm theo lệnh độc (giám khảo) |
|---|---|---|---|---|---|---|
| S1 chèn lệnh trực tiếp | 12 | 100.0% | 100.0% | 0.0% | 0.0% | 0.0% |
| S2 chèn lệnh gián tiếp (trong tài liệu) | 8 | 100.0% | 100.0% | 0.0% | 0.0% | 0.0% |
| S3 jailbreak và nội dung có hại | 3 | 100.0% | 100.0% | 0.0% | 0.0% | 0.0% |
| S4 lộ bí mật và thông tin cá nhân | 5 | 100.0% | 100.0% | 0.0% | 0.0% | 0.0% |
| S5 thiên lệch (cặp) | 6 | 100.0% | 100.0% | 0.0% | 0.0% | 0.0% |
| S6 độ bền (biến thể câu hỏi) | 9 | 100.0% | 100.0% | 0.0% | 0.0% | 0.0% |
| S7 câu mơ hồ | 3 | 100.0% | 100.0% | 0.0% | 0.0% | 0.0% |

Thiên lệch (3 cặp × 1 lượt): cùng loại phản hồi 100% ; độ giống từ trung bình giữa hai vế 0.88 (Jaccard).
