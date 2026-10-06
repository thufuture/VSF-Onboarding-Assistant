### Độ chính xác (cộng cả các lượt chạy)
| Phương án | 26 câu tài liệu | 10 câu định tuyến | 4 câu nhiều ý | Tổng ✓ |
|---|---|---|---|---|
| A. Hiện trạng (thinking bật ở cả 3 bước) | 47/52 ✓ · 5 ~ · 0 ✗ | 18/20 ✓ · 0 ~ · 2 ✗ | 8/8 ✓ · 0 ~ · 0 ✗ | **73/80** (91.2%) |
| B. Tắt thinking ở route + rewrite | 50/52 ✓ · 2 ~ · 0 ✗ | 18/20 ✓ · 0 ~ · 2 ✗ | 7/8 ✓ · 1 ~ · 0 ✗ | **75/80** (93.8%) |
| C. Tắt thinking ở cả route, rewrite, answer | 47/52 ✓ · 4 ~ · 1 ✗ | 18/20 ✓ · 0 ~ · 2 ✗ | 6/8 ✓ · 2 ~ · 0 ✗ | **71/80** (88.8%) |

### Độ trễ một câu hỏi (giây, đo ở phía người dùng)
| Phương án | Trung vị | Trung bình | p95 | Lớn nhất | Số lượt |
|---|---|---|---|---|---|
| A. Hiện trạng (thinking bật ở cả 3 bước) | 7.66 | 7.10 | 13.98 | 18.86 | 80 |
| B. Tắt thinking ở route + rewrite | 5.95 | 5.60 | 10.67 | 22.12 | 80 |
| C. Tắt thinking ở cả route, rewrite, answer | 5.21 | 4.44 | 6.94 | 8.12 | 80 |

### Độ trễ trung bình mỗi lần gọi (giây)
| Phương án | viga.route | chat.rewrite | chat.embed | chat.answer |
|---|---|---|---|---|
| A. Hiện trạng (thinking bật ở cả 3 bước) | 1.61 | 2.25 | 1.79 | 3.29 |
| B. Tắt thinking ở route + rewrite | 1.08 | 1.05 | 1.75 | 3.30 |
| C. Tắt thinking ở cả route, rewrite, answer | 1.11 | 1.12 | 1.73 | 1.63 |

### Token đầu ra trung bình mỗi lần gọi (gồm cả suy luận ẩn)
| Phương án | viga.route | chat.rewrite | chat.embed | chat.answer |
|---|---|---|---|---|
| A. Hiện trạng (thinking bật ở cả 3 bước) | 151 | 311 | 0 | 605 |
| B. Tắt thinking ở route + rewrite | 43 | 33 | 0 | 621 |
| C. Tắt thinking ở cả route, rewrite, answer | 44 | 33 | 0 | 149 |

### Trong đó token suy luận ẩn
| Phương án | viga.route | chat.rewrite | chat.embed | chat.answer |
|---|---|---|---|---|
| A. Hiện trạng (thinking bật ở cả 3 bước) | 108 | 275 | 0 | 442 |
| B. Tắt thinking ở route + rewrite | 0 | 0 | 0 | 460 |
| C. Tắt thinking ở cả route, rewrite, answer | 0 | 0 | 0 | 0 |

### Token đầu vào trung bình mỗi lần gọi
| Phương án | viga.route | chat.rewrite | chat.embed | chat.answer |
|---|---|---|---|---|
| A. Hiện trạng (thinking bật ở cả 3 bước) | 1201 | 384 | 0 | 7785 |
| B. Tắt thinking ở route + rewrite | 1176 | 359 | 0 | 7465 |
| C. Tắt thinking ở cả route, rewrite, answer | 1176 | 359 | 0 | 7503 |

### Chi phí ước tính mỗi câu hỏi (mili-USD; cột cuối: USD cho 1.000 câu)
| Phương án | Tổng/câu | viga.route | chat.rewrite | chat.embed | chat.answer | USD/1.000 câu |
|---|---|---|---|---|---|---|
| A. Hiện trạng (thinking bật ở cả 3 bước) | 3.461 | 0.501 | 0.366 | 0.297 | 2.296 | 3.46 |
| B. Tắt thinking ở route + rewrite | 2.971 | 0.374 | 0.109 | 0.286 | 2.201 | 2.97 |
| C. Tắt thinking ở cả route, rewrite, answer | 2.560 | 0.376 | 0.109 | 0.283 | 1.792 | 2.56 |

### Số câu đổi kết quả so với hiện trạng (cùng câu, cùng lượt)
| Phương án | Đổi kết quả | Tệ đi | Tốt lên |
|---|---|---|---|
| B. Tắt thinking ở route + rewrite | 4 | 1 | 3 |
| C. Tắt thinking ở cả route, rewrite, answer | 6 | 4 | 2 |
