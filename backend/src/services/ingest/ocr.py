"""OCR cho PDF scan bằng OCRmyPDF + Tesseract (gói tiếng Việt `vie`): thêm lớp chữ vào PDF ảnh để đọc/tìm kiếm được.

Đã đo (09/10/2026) trên bản "scan" giả của PUB_R03 (5 trang, 200 dpi, nghiêng nhẹ, JPEG chất lượng 55): CER 0,99% (bỏ dấu 0,47%),
WER 2,95%, 3 trên 69 số liệu bị sai hoặc mất, khoảng 5,6 giây CPU mỗi trang. Chưa đo trên scan thật hay ảnh chụp điện thoại: kết quả OCR
luôn phải được HR soát lại (nhất là số liệu, ngày tháng) trước khi kích hoạt.

Chạy ở tiến trình nền (job), `nice` thấp để không tranh CPU với embedding và API. Dùng `--force-ocr` (không dùng `--skip-text`: Ghostscript 10.0 của Debian bookworm bị ocrmypdf từ chối vì lỗi làm hỏng PDF).
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class OcrError(Exception):
    """OCR không chạy được hoặc thất bại (thiếu công cụ, quá nhiều trang, file hỏng, quá giờ)."""


def ocr_pdf(pdf: bytes, *, languages: str, max_pages: int, jobs: int, timeout_seconds: int) -> bytes:
    """Chạy đồng bộ (nặng CPU, gọi qua `asyncio.to_thread`); trả PDF có lớp chữ."""
    binary = shutil.which("ocrmypdf")
    if binary is None:
        raise OcrError("chưa cài ocrmypdf và tesseract trong môi trường chạy")
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "in.pdf"
        target = Path(directory) / "out.pdf"
        source.write_bytes(pdf)
        try:
            import pikepdf

            with pikepdf.open(source) as document:
                pages = len(document.pages)
        except Exception as exc:
            raise OcrError("không đọc được PDF") from exc
        if pages == 0 or pages > max_pages:
            raise OcrError(f"PDF có {pages} trang, giới hạn {max_pages}")
        command = [
            binary,
            "-l",
            languages,
            "--force-ocr",
            "--jobs",
            str(jobs),
            "--output-type",
            "pdf",
            "--optimize",
            "0",
            "--quiet",
        ]
        nice = shutil.which("nice")
        if nice:
            command = [nice, "-n", "15", *command]
        command += [str(source), str(target)]
        try:
            completed = subprocess.run(command, capture_output=True, timeout=timeout_seconds, check=False)
        except subprocess.TimeoutExpired as exc:
            raise OcrError("OCR quá thời gian cho phép") from exc
        if completed.returncode != 0 or not target.exists():
            tail = completed.stderr.decode("utf-8", errors="replace").strip().splitlines()[-1:] or [""]
            logger.warning("ocr_failed code=%s detail=%s", completed.returncode, tail[0][:200])
            raise OcrError(f"ocrmypdf lỗi (mã {completed.returncode})")
        return target.read_bytes()
