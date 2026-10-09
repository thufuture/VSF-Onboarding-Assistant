# Embedding BGE-M3 chạy trên MÁY DEV (CPU), dùng cùng mã nguồn với production nhưng CỐ ĐỊNH đúng bản mô hình.
# Build (ngữ cảnh là thư mục deploy/aws/embedder, KHÔNG sửa các tệp ở đó vì deploy production băm chúng):
#   docker build -t vsf-embedder:local -f scripts/dev/embedder-local/Dockerfile deploy/aws/embedder
# Vì sao cố định bản: DB dev lưu embedding_model_version = BAAI/bge-m3@<mã bản> và truy hồi lọc đúng theo chuỗi này; nếu Hugging
# Face đã có bản mới hơn thì vector khác và tìm kiếm trả rỗng. Chỉ tải các tệp cần (bỏ onnx, ảnh) để ảnh nhẹ hơn production.
FROM python:3.12-slim

ARG TORCH_INDEX=https://download.pytorch.org/whl/cpu
ARG BGE_REVISION=5617a9f61b028005a4858fdac845db406aefb181
ENV PIP_NO_CACHE_DIR=1 PYTHONUNBUFFERED=1 HF_HOME=/models BGE_REVISION=${BGE_REVISION}

WORKDIR /app
RUN pip install torch --index-url ${TORCH_INDEX}
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN python -c "import os, pathlib; from huggingface_hub import snapshot_download; rev = os.environ['BGE_REVISION']; snapshot_download('BAAI/bge-m3', revision=rev, ignore_patterns=['onnx/*', '*.msgpack', '*.h5', '*.ot', 'imgs/*', '*.jpg', '*.png']); refs = pathlib.Path('/models/hub/models--BAAI--bge-m3/refs'); refs.mkdir(parents=True, exist_ok=True); (refs / 'main').write_text(rev)"
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-m3')"

COPY server.py .
EXPOSE 8080
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
