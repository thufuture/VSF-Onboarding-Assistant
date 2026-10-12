"""Dịch vụ rerank thử nghiệm: BAAI/bge-reranker-v2-m3 (cross-encoder) qua HTTP, chạy trong ảnh vsf-embedder:local (torch CPU).

Chỉ dùng cho benchmark, KHÔNG phải mã sản phẩm. Khởi chạy bằng run_reranker.sh (giới hạn 2 CPU để sát máy 2 vCPU trên AWS).
POST /rerank {"query": str, "passages": [str, ...], "max_length": int (tùy chọn)} -> {"scores": [float, ...], "seconds": float}
"""

import os
import time

import torch
from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import CrossEncoder

MODEL = os.environ.get("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")
torch.set_num_threads(int(os.environ.get("RERANK_THREADS", "2")))
DEFAULT_MAX_LEN = int(os.environ.get("RERANK_MAX_LEN", "512"))
model = CrossEncoder(MODEL, max_length=DEFAULT_MAX_LEN, device="cpu")
if os.environ.get("RERANK_INT8") == "1":  # lượng tử hóa động int8 cho các lớp tuyến tính (CPU): nhanh hơn, cần đo lại chất lượng
    torch.quantization.quantize_dynamic(model.model, {torch.nn.Linear}, dtype=torch.qint8, inplace=True)
app = FastAPI()


class Request(BaseModel):
    query: str
    passages: list[str]
    max_length: int | None = None  # ghi đè độ dài tối đa mỗi cặp cho lời gọi này (để quét 512 / 256)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": MODEL, "int8": os.environ.get("RERANK_INT8") == "1", "threads": torch.get_num_threads()}


@app.post("/rerank")
def rerank(request: Request) -> dict:
    started = time.perf_counter()
    model.max_length = request.max_length or DEFAULT_MAX_LEN
    scores = model.predict([(request.query, passage) for passage in request.passages], batch_size=8, show_progress_bar=False)
    return {"scores": [float(s) for s in scores], "seconds": round(time.perf_counter() - started, 4)}
