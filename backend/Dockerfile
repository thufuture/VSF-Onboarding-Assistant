# ---- Tầng 1: cài phụ thuộc ----
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# ---- Tầng 2: chạy ----
FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=builder /opt/venv /opt/venv

# OCR cho PDF scan (OCR_ENABLED): Tesseract kèm gói tiếng Việt và Ghostscript.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-vie tesseract-ocr-eng ghostscript \
    && rm -rf /var/lib/apt/lists/*

# uid cố định, không chạy bằng root.
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app

COPY --chown=appuser:appuser src ./src
COPY --chown=appuser:appuser alembic.ini ./
COPY --chown=appuser:appuser alembic ./alembic

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
