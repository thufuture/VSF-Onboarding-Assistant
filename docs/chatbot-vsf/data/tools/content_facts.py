"""Ràng buộc nhất quán cho tài liệu dài: số từ tối thiểu, chuỗi bị cấm, tên miền/email/URL được phép."""
from __future__ import annotations

# Số từ tối thiểu của bản dài (≈70% mục tiêu). Tài liệu không có trong bảng thì không kiểm.
MIN_WORDS = {
    "D01": 2400, "D02": 1200, "D03a": 1200, "D03b": 2400, "D03c": 1200, "D04": 2200,
    "D05": 2400, "D06": 1000, "D07": 1900, "D08a": 1200, "D08b": 2200, "D09": 2200, "D10": 2100, "D11": 1100,
    "P01": 2600, "P01b": 2600, "P02": 1500, "P03": 2200, "P04": 1900, "P05": 1800, "P10": 1600,
    "P06": 2900, "P07": 2900, "P08": 2500, "P09": 2200, "D13": 2100, "E09": 1700, "E06": 1200, "E10": 800, "E03": 1100,
    "D12": 6500, "E04": 800, "E02": 700,
}

# Chuỗi KHÔNG được xuất hiện trong tài liệu (tránh mâu thuẫn dữ kiện giữa các phiên bản). Lịch sử sửa đổi chỉ mô tả
# thay đổi bằng lời, không nêu con số cũ.
FORBIDDEN = {
    "D03a": ["12 ngày", "13 ngày", "15 ngày", "16 ngày"],
    "D03b": ["10 ngày", "13 ngày", "15 ngày", "16 ngày"],
    "D03c": ["10 ngày", "12 ngày", "15 ngày", "16 ngày"],
    "D08a": ["12 ký tự", "90 ngày"],
    "D08b": ["8 ký tự", "180 ngày"],
    "P01": ["8:30"],
    "P01b": ["8:15"],
}

ALLOWED_URL_HOST_SUFFIXES = ("vsf-demo.example",)
# URL có scheme chỉ được phép ở các tài liệu này với tên miền tương ứng (kiểm thử link giả/chèn lệnh).
URL_EXCEPTIONS = {"E09": ("malicious.example",), "P06": ("tools.vsf-demo.example",)}
EMAIL_ALLOW_DOMAINS = ("vsf-demo.example",)
PHONE_PATTERN = r"(?<!\d)0\d{8,10}(?!\d)|1900\s?\d{3,}"
