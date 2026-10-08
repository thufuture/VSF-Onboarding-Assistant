# -*- coding: utf-8 -*-
"""Dịch vụ embedding BGE-M3 tự host: cùng hợp đồng HTTP với app Modal `ralion-bge-m3-embedder`, nên backend chỉ cần đổi
`EMBEDDING_ENDPOINT` và `EMBEDDING_API_KEY`, không sửa mã.

    POST /embed   {"texts": ["...", ...]}            (tối đa 32 chuỗi/lần)
                  Authorization: Bearer <EMBEDDING_API_KEY>
               -> {"vectors": [[...1024 số...]], "model_version": "bge-m3", "dimension": 1024}
    GET  /health  -> {"status": "ok", "model": ..., "device": ..., "dtype": ...}

Chỉ trả vector dense (đã chuẩn hóa L2), đúng thứ tự đầu vào, đúng như adapter Modal của backend đang đọc.

Biến môi trường:
    EMBEDDING_API_KEY   bắt buộc: khóa Bearer (không có thì không chạy, tránh mở dịch vụ không khóa ra mạng)
    MODEL_NAME          mặc định BAAI/bge-m3
    DTYPE               fp32 (mặc định) | bf16 (nhanh hơn trên CPU có AMX như Intel Sapphire Rapids: họ m7i/c7i; GPU thì dùng fp16)
    MAX_LENGTH          số token tối đa mỗi chuỗi, mặc định 512 (đủ cho chunk của dự án)
    MODEL_VERSION       ghi đè chuỗi phiên bản trả về; mặc định tự lấy dạng BAAI/bge-m3@<mã bản HF> như app Modal
                        (phải trùng giá trị đang lưu ở document_chunks.embedding_model_version, lệch thì tìm kiếm trả rỗng)
    TORCH_THREADS       số luồng CPU, mặc định = số lõi
"""

import hmac
import os
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

import torch
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

MAX_BATCH = 32
API_KEY = os.environ.get("EMBEDDING_API_KEY", "")
MODEL_NAME = os.environ.get("MODEL_NAME", "BAAI/bge-m3")
MAX_LENGTH = int(os.environ.get("MAX_LENGTH", "512"))
DTYPE_NAME = os.environ.get("DTYPE", "fp32").lower()
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DTYPES = {"fp32": torch.float32, "bf16": torch.bfloat16, "fp16": torch.float16}

if not API_KEY:
    raise SystemExit("Thiếu EMBEDDING_API_KEY: từ chối chạy dịch vụ embedding không có khóa.")
if DTYPE_NAME not in DTYPES:
    raise SystemExit(f"DTYPE không hợp lệ: {DTYPE_NAME}")

def _resolve_model_version() -> str:
    """Chuỗi phiên bản trả về cho backend: PHẢI trùng giá trị đang lưu ở `document_chunks.embedding_model_version`, vì truy hồi
    lọc theo đúng chuỗi này (lệch một ký tự thì tìm kiếm trả rỗng). App Modal trả `BAAI/bge-m3@<mã bản Hugging Face>`; ở đây lấy
    cùng dạng từ bộ nhớ đệm Hugging Face (refs/main). Đặt MODEL_VERSION để ghi đè khi cần."""
    explicit = os.environ.get("MODEL_VERSION")
    if explicit:
        return explicit
    home = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface"))
    ref = home / "hub" / ("models--" + MODEL_NAME.replace("/", "--")) / "refs" / "main"
    try:
        return f"{MODEL_NAME}@{ref.read_text().strip()}"
    except OSError:
        return MODEL_NAME


MODEL_VERSION = "unknown"
_model: SentenceTransformer | None = None
_lock = threading.Lock()  # một lần suy luận một lúc: nhiều luồng cùng chạy trên CPU chỉ chậm hơn


@asynccontextmanager
async def lifespan(_: FastAPI):
    global _model, MODEL_VERSION
    threads = int(os.environ.get("TORCH_THREADS", "0")) or (os.cpu_count() or 1)
    torch.set_num_threads(threads)
    started = time.perf_counter()
    model = SentenceTransformer(MODEL_NAME, device=DEVICE)
    model.max_seq_length = MAX_LENGTH
    model = model.to(dtype=DTYPES[DTYPE_NAME])
    model.eval()
    with torch.inference_mode():  # chạy nóng một lần để lần gọi đầu tiên của người dùng không phải trả giá khởi tạo
        model.encode(["khởi động"], normalize_embeddings=True)
    _model = model
    MODEL_VERSION = _resolve_model_version()
    print(f"[embedder] {MODEL_VERSION} · {DEVICE} · {DTYPE_NAME} · {threads} luồng · nạp xong sau {time.perf_counter() - started:.1f}s", flush=True)
    yield


app = FastAPI(lifespan=lifespan, title="bge-m3-embedder")


class EmbedRequest(BaseModel):
    texts: list[str] = Field(min_length=1, max_length=MAX_BATCH)


def _check_key(authorization: str | None) -> None:
    expected = f"Bearer {API_KEY}"
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="unauthorized")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok" if _model is not None else "loading", "model": MODEL_NAME, "device": DEVICE, "dtype": DTYPE_NAME}


@app.post("/embed")
def embed(body: EmbedRequest, authorization: str | None = Header(default=None)) -> dict[str, object]:
    _check_key(authorization)
    if _model is None:
        raise HTTPException(status_code=503, detail="model chưa nạp xong")
    with _lock, torch.inference_mode():
        vectors = _model.encode(body.texts, batch_size=MAX_BATCH, normalize_embeddings=True, convert_to_numpy=True)
    return {"vectors": vectors.astype("float32").tolist(), "model_version": MODEL_VERSION, "dimension": int(vectors.shape[1])}
