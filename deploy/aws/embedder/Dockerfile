# Dịch vụ embedding BGE-M3 tự host (CPU mặc định; GPU: --build-arg TORCH_INDEX=https://download.pytorch.org/whl/cu124).
# Mô hình (~2,3 GB) được tải sẵn vào ảnh lúc build để container khởi động không phải tải lại từ Hugging Face.
FROM python:3.12-slim

ARG TORCH_INDEX=https://download.pytorch.org/whl/cpu
ENV PIP_NO_CACHE_DIR=1 PYTHONUNBUFFERED=1 HF_HOME=/models

WORKDIR /app
RUN pip install torch --index-url ${TORCH_INDEX}
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-m3')"

COPY server.py .
EXPOSE 8080
# EMBEDDING_API_KEY phải được truyền lúc chạy (docker run -e / env-file), không bao giờ ghi vào ảnh.
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
