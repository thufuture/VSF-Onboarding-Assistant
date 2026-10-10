"""Đo độ chính xác, tốc độ, bộ nhớ của Tesseract (vie+eng) trên trang scan giả có đáp án.

Chạy trong ảnh backend (đã có tesseract, pypdfium2, pillow, pdfminer):
  docker run --rm --cpus 2 -v <repo>/docs/chatbot-vsf/data/documents:/d:ro -v <repo>/docs/value/benchmark-ocr:/b \
      vsf-onboarding-backend python /b/scripts/do_ocr_tesseract.py /d /b/ket-qua/ocr-tesseract.json

Đáp án = lớp chữ của PDF gốc (pdfminer). Mỗi trang được vẽ thành ảnh rồi cho xuống cấp theo 3 điều kiện; so chữ OCR với đáp án sau khi chuẩn hóa
(Unicode NFC, bỏ mọi khoảng trắng để không phạt khác biệt ngắt dòng). Số liệu = các chuỗi có chữ số trong đáp án.
"""

import collections
import io
import json
import os
import random
import re
import resource
import statistics
import subprocess
import sys
import tempfile
import time
import unicodedata
from pathlib import Path

import pypdfium2 as pdfium
from pdfminer.high_level import extract_text
from PIL import Image, ImageFilter

ROOT = Path(sys.argv[1])
OUT = Path(sys.argv[2])
LANG = os.environ.get("OCR_LANG", "vie+eng")
THREADS = os.environ.get("OMP_THREAD_LIMIT", "2")

PAGES = [  # (tệp, trang bắt đầu từ 1, nhóm)
    ("real_public/PUB_R03_Luat_Cong_doan_50-2024-QH15.pdf", 5, "luật (văn xuôi dài)"),
    ("real_public/PUB_R03_Luat_Cong_doan_50-2024-QH15.pdf", 12, "luật (văn xuôi dài)"),
    ("real_public/PUB_R03_Luat_Cong_doan_50-2024-QH15.pdf", 18, "luật (văn xuôi dài)"),
    ("real_public/PUB_R04_Thong_tu_10-2020-TT-BLDTBXH.pdf", 6, "thông tư (điều khoản, số hiệu)"),
    ("core/SYN_D05_Phuc_loi_va_bao_hiem.pdf", 1, "nội quy/chính sách"),
    ("core/SYN_P02_Lich_tuan_dau_tien.pdf", 1, "bảng lịch"),
    ("format_edge/SYN_E02_Bang_thuong_hieu_suat.pdf", 1, "bảng số liệu"),
    ("core/SYN_D10_Bao_cao_su_co_bao_mat.pdf", 1, "nội quy/chính sách"),
]
CONDITIONS = {
    "sạch 200 dpi": dict(dpi=200, angle=0.0, blur=0.0, jpeg=None),
    "sạch 300 dpi": dict(dpi=300, angle=0.0, blur=0.0, jpeg=None),
    "xuống cấp (150 dpi, nghiêng 1,5°, mờ, JPEG 40)": dict(dpi=150, angle=1.5, blur=0.7, jpeg=40),
}


def norm(text: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFC", text))


def strip_marks(text: str) -> str:
    text = unicodedata.normalize("NFD", text).replace("đ", "d").replace("Đ", "D")
    return unicodedata.normalize("NFC", "".join(c for c in text if unicodedata.category(c) != "Mn"))


def edit_distance(a: str, b: str) -> int:
    """Levenshtein hai hàng; đủ nhanh cho trang vài nghìn ký tự."""
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


def words(text: str) -> list[str]:
    return re.findall(r"\w+", unicodedata.normalize("NFC", text).lower())


def number_tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"\d[\d.,/-]*\d|\d", unicodedata.normalize("NFC", text))]


def wer(got: list[str], want: list[str]) -> float:
    """Tỉ lệ từ sai theo khoảng cách sửa ở mức từ (nhanh bằng ánh xạ từ sang ký tự)."""
    vocabulary = {w: chr(0x4E00 + i) for i, w in enumerate(sorted(set(got) | set(want)))}
    a = "".join(vocabulary[w] for w in got)
    b = "".join(vocabulary[w] for w in want)
    return edit_distance(a, b) / max(1, len(want))


def render(path: Path, page_number: int, cond: dict[str, object], seed: int) -> Image.Image:
    document = pdfium.PdfDocument(str(path))
    image = document[page_number - 1].render(scale=int(cond["dpi"]) / 72).to_pil().convert("L")  # type: ignore[call-overload]
    random.seed(seed)
    angle = float(cond["angle"])  # type: ignore[arg-type]
    if angle:
        image = image.rotate(random.choice([-1, 1]) * angle, expand=True, fillcolor=255)
    if cond["blur"]:
        image = image.filter(ImageFilter.GaussianBlur(float(cond["blur"])))  # type: ignore[arg-type]
    if cond["jpeg"]:
        buffer = io.BytesIO()
        image.save(buffer, "JPEG", quality=int(cond["jpeg"]))  # type: ignore[call-overload]
        image = Image.open(io.BytesIO(buffer.getvalue())).convert("L")
    return image


def tesseract(image: Image.Image) -> tuple[str, float]:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "p.png"
        image.save(path)
        started = time.perf_counter()
        result = subprocess.run(
            ["tesseract", str(path), "-", "-l", LANG, "--psm", "3"],
            capture_output=True,
            text=True,
            check=True,
            env={**os.environ, "OMP_THREAD_LIMIT": THREADS},
        )
        return result.stdout, time.perf_counter() - started


rows = []
for number, (relative, page_number, group) in enumerate(PAGES):
    pdf = ROOT / relative
    truth = extract_text(str(pdf), page_numbers=[page_number - 1])
    truth_chars = norm(truth)
    truth_plain = strip_marks(truth_chars)
    truth_words = words(truth)
    truth_numbers = number_tokens(truth)
    for label, cond in CONDITIONS.items():
        text, seconds = tesseract(render(pdf, page_number, cond, seed=number))
        got = norm(text)
        cer = edit_distance(got, truth_chars) / max(1, len(truth_chars))
        cer_plain = edit_distance(strip_marks(got), truth_plain) / max(1, len(truth_plain))
        have = collections.Counter(number_tokens(text))
        need = collections.Counter(truth_numbers)
        hit = sum(min(have[k], c) for k, c in need.items())
        rows.append(
            {
                "tệp": relative.split("/")[-1],
                "trang": page_number,
                "nhóm": group,
                "điều kiện": label,
                "ký_tự_đáp_án": len(truth_chars),
                "CER_%": round(100 * cer, 2),
                "CER_bỏ_dấu_%": round(100 * cer_plain, 2),
                "WER_%": round(100 * wer(words(text), truth_words), 2),
                "số_liệu_đúng": hit,
                "số_liệu_tổng": len(truth_numbers),
                "giây": round(seconds, 2),
            }
        )
        print(rows[-1], flush=True)

summary = {}
for label in CONDITIONS:
    part = [r for r in rows if r["điều kiện"] == label]
    seconds = sorted(r["giây"] for r in part)
    summary[label] = {
        "số_trang": len(part),
        "CER_trung_bình_%": round(statistics.mean(r["CER_%"] for r in part), 2),
        "CER_trung_vị_%": round(statistics.median(r["CER_%"] for r in part), 2),
        "CER_xấu_nhất_%": max(r["CER_%"] for r in part),
        "CER_bỏ_dấu_trung_bình_%": round(statistics.mean(r["CER_bỏ_dấu_%"] for r in part), 2),
        "WER_trung_bình_%": round(statistics.mean(r["WER_%"] for r in part), 2),
        "số_liệu_đúng_%": round(100 * sum(r["số_liệu_đúng"] for r in part) / max(1, sum(r["số_liệu_tổng"] for r in part)), 1),
        "giây_mỗi_trang_trung_vị": round(statistics.median(seconds), 2),
        "giây_mỗi_trang_lớn_nhất": seconds[-1],
    }
peak_mb = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024
engine = subprocess.run(["tesseract", "--version"], capture_output=True, text=True).stdout.splitlines()[0]
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(
    json.dumps(
        {"engine": engine, "ngôn_ngữ": LANG, "luồng": THREADS, "RAM_đỉnh_một_tiến_trình_MB": round(peak_mb), "tóm_tắt": summary, "chi_tiết": rows},
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
print(json.dumps(summary, ensure_ascii=False, indent=2))
print("RAM đỉnh (MB):", round(peak_mb))
