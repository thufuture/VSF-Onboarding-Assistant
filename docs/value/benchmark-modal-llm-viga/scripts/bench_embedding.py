# -*- coding: utf-8 -*-
"""So sánh dịch vụ embedding Modal (đang dùng) với BGE-M3 tự host: độ trễ (chủ yếu) và độ chính xác.

Độ trễ:  mỗi câu golden gọi N lần tuần tự cho từng nguồn, xen kẽ hai nguồn để cùng điều kiện mạng; thêm một lô 32 đoạn thật.
Chính xác:
  1. cosine giữa vector của hai nguồn cho cùng một câu hỏi (cùng mô hình thì phải ≈ 1,0);
  2. cosine giữa vector đã lưu trong DB (do Modal nhúng lúc nạp tài liệu) và vector nhúng lại bằng nguồn tự host cho CÙNG đoạn văn;
  3. truy hồi: với từng câu golden, top-5 đoạn gần nhất theo vector của mỗi nguồn trên DB thật: độ trùng top-5 giữa hai nguồn,
     và hit@5 (top-5 có chứa ít nhất một ý bắt buộc must_contain của câu đó).

Chạy:  SELF_EMBED_URL=http://<ip>:8080 SELF_EMBED_KEY=<khóa> python bench_embedding.py --label tu_host_aws --repeat 5
Khóa Modal và DATABASE_URL đọc từ .env; mọi khóa không bao giờ được in ra.
"""

import argparse
import asyncio
import json
import os
import statistics
import time
from pathlib import Path

import asyncpg
import httpx

ROOT = Path(__file__).resolve().parents[4]
BASE = Path(__file__).resolve().parents[1]
BATCH = 32


def read_env(name: str) -> str:
    value = os.environ.get(name)
    if value:
        return value
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{name}="):
            return line.split("=", 1)[1].strip().strip('"')
    raise SystemExit(f"thiếu {name}")


def pct(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(q * (len(ordered) - 1)))]


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb)


class Provider:
    def __init__(self, name: str, url: str, key: str) -> None:
        self.name = name
        self.url = url.rstrip("/") + "/embed"
        self.key = key
        self.client = httpx.Client(timeout=180)

    def embed(self, texts: list[str]) -> tuple[list[list[float]], float]:
        started = time.perf_counter()
        response = self.client.post(self.url, json={"texts": texts}, headers={"Authorization": f"Bearer {self.key}"})
        seconds = time.perf_counter() - started
        response.raise_for_status()
        return response.json()["vectors"], seconds


def vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(repr(v) for v in vector) + "]"


async def db_part(questions: list[dict], vectors: dict[str, dict[int, list[float]]], batch_texts: list[str] | None, self_vectors_for_chunks: callable) -> dict:
    connection = await asyncpg.connect(read_env("DATABASE_URL").replace("+asyncpg", ""))
    try:
        # Chuỗi phiên bản đang lưu ở DB (Modal trả BAAI/bge-m3@<mã bản>): truy hồi của backend lọc đúng theo chuỗi này.
        model_version = await connection.fetchval("SELECT embedding_model_version FROM document_chunks WHERE embedding IS NOT NULL LIMIT 1")
        # 2. nhúng lại đoạn thật bằng nguồn tự host và so với vector Modal đã lưu
        rows = await connection.fetch(
            """SELECT c.id, c.embedding_text, c.embedding::text AS emb FROM document_chunks c
               JOIN document_versions v ON v.id = c.version_id
               WHERE v.status = 'ACTIVE' AND c.embedding IS NOT NULL ORDER BY c.id LIMIT 64"""
        )
        stored = [(r["id"], r["embedding_text"], [float(x) for x in r["emb"].strip("[]").split(",")]) for r in rows]
        re_embedded = self_vectors_for_chunks([text for _, text, _ in stored])
        chunk_cos = [cosine(old, new) for (_, _, old), new in zip(stored, re_embedded, strict=True)]
        # 3. truy hồi top-5 theo từng nguồn
        retrieval = {}
        for name, per_question in vectors.items():
            tops = {}
            for q in questions:
                found = await connection.fetch(
                    """SELECT c.id, c.content FROM document_chunks c
                       JOIN document_versions v ON v.id = c.version_id JOIN documents d ON d.id = v.document_id
                       WHERE v.status = 'ACTIVE' AND d.status = 'ACTIVE' AND c.embedding_model_version = $2
                       ORDER BY c.embedding <=> $1::vector LIMIT 5""",
                    vector_literal(per_question[q["id"]]),
                    model_version,
                )
                tops[q["id"]] = [(r["id"], r["content"].lower()) for r in found]
            retrieval[name] = tops
        return {"chunk_cos": chunk_cos, "retrieval": retrieval, "chunk_count": len(stored)}
    finally:
        await connection.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--repeat", type=int, default=5)
    args = parser.parse_args()

    golden = json.loads((BASE / "golden_set.json").read_text(encoding="utf-8"))["cases"]
    modal = Provider("modal", read_env("EMBEDDING_ENDPOINT"), read_env("EMBEDDING_API_KEY"))
    own = Provider("tu_host", os.environ["SELF_EMBED_URL"], os.environ["SELF_EMBED_KEY"])
    providers = [modal, own]

    for provider in providers:  # làm ấm: lần đầu của Modal có thể mất hàng chục giây vì GPU nguội, không tính vào số đo
        provider.embed(["khởi động"])

    latency: dict[str, list[float]] = {p.name: [] for p in providers}
    first_vector: dict[str, dict[int, list[float]]] = {p.name: {} for p in providers}
    for case in golden:
        for repeat in range(args.repeat):
            for provider in providers:
                vecs, seconds = provider.embed([case["question"]])
                latency[provider.name].append(seconds * 1000)
                if repeat == 0:
                    first_vector[provider.name][case["id"]] = vecs[0]
        print(f"#{case['id']} modal={statistics.median(latency['modal'][-args.repeat:]):.0f}ms tu_host={statistics.median(latency['tu_host'][-args.repeat:]):.0f}ms", flush=True)

    question_cos = [cosine(first_vector["modal"][c["id"]], first_vector["tu_host"][c["id"]]) for c in golden]

    # lô 32 đoạn thật
    chunk_texts_holder: list[str] = []

    def self_vectors_for_chunks(texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), BATCH):
            out.extend(own.embed(texts[i : i + BATCH])[0])
        return out

    db = asyncio.run(db_part(golden, first_vector, chunk_texts_holder, self_vectors_for_chunks))

    batch_latency: dict[str, list[float]] = {p.name: [] for p in providers}
    sample = [f"đoạn văn thử số {i} " + "nội dung onboarding " * 20 for i in range(BATCH)]
    for _ in range(3):
        for provider in providers:
            batch_latency[provider.name].append(provider.embed(sample)[1] * 1000)

    overlap = []
    hits = {"modal": [0, 0], "tu_host": [0, 0]}
    for case in golden:
        modal_ids = [i for i, _ in db["retrieval"]["modal"][case["id"]]]
        own_ids = [i for i, _ in db["retrieval"]["tu_host"][case["id"]]]
        overlap.append(len(set(modal_ids) & set(own_ids)) / 5)
        if case["expect"] == "ANSWER" and case["must_contain"]:
            for name in hits:
                text = " ".join(t for _, t in db["retrieval"][name][case["id"]])
                hits[name][1] += 1
                hits[name][0] += any(m.lower() in text for m in case["must_contain"])

    result = {
        "label": args.label,
        "repeat": args.repeat,
        "latency_ms": {name: {"p50": pct(v, 0.5), "p95": pct(v, 0.95), "mean": statistics.mean(v), "min": min(v), "max": max(v), "n": len(v)} for name, v in latency.items()},
        "batch32_ms": {name: {"p50": pct(v, 0.5), "mean": statistics.mean(v)} for name, v in batch_latency.items()},
        "cosine_question": {"mean": statistics.mean(question_cos), "min": min(question_cos)},
        "cosine_stored_chunks": {"mean": statistics.mean(db["chunk_cos"]), "min": min(db["chunk_cos"]), "n": db["chunk_count"]},
        "top5_overlap_mean": statistics.mean(overlap),
        "hit_at_5": {name: {"hit": h, "of": n} for name, (h, n) in hits.items()},
    }
    out = BASE / "ket-qua" / f"embedding_{args.label}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))


main()
