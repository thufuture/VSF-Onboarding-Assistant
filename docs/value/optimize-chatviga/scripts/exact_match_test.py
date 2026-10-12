"""Đo truy hồi (KHÔNG gọi LLM) trên 10 câu cần khớp đúng chuỗi: mã form, email, địa chỉ, viết tắt kỹ thuật.

Mục đích: kiểm tra rủi ro "thiên vị vector" của RRF tối ưu (BM25 chỉ 0,1). So các cách xếp hạng:
  BM25 riêng | vector riêng | RRF mặc định (k=60, 1:1) | RRF tối ưu (k=10, 0,1:1) | RRF k=10, 0,5:1
  | tối ưu + giữ chỗ BM25 (4 mục đầu của RRF tối ưu + mục đứng đầu của BM25 nếu chưa có)
Nhãn: mọi mục chứa đúng chuỗi cần khớp (bo-cau-hoi/khop_chinh_xac_10.json). Chạy trên bản chụp `vsf_bench`, chỉ đọc.

Chạy từ gốc repo:
  PYTHONIOENCODING=utf-8 PYTHONPATH=backend backend/.venv/Scripts/python.exe docs/value/optimize-chatviga/scripts/exact_match_test.py
"""

import asyncio
import json
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(DIR / "scripts"))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from src.api import dependencies as deps  # noqa: E402
from src.config import get_settings  # noqa: E402
from src.services.ingest.lexical import to_lexical_text  # noqa: E402
from src.services.retrieval.hybrid_search import _bm25_search, _dense_search  # noqa: E402
from sweep_rrf import fuse  # noqa: E402


def bm25_sections(bm25: list[tuple[int, int]]) -> list[int]:
    seen: list[int] = []
    for _, section_id in bm25:
        if section_id not in seen:
            seen.append(section_id)
    return seen


def rank_of(order: list[int], gold: set[int]) -> int | None:
    return next((i + 1 for i, sid in enumerate(order) if sid in gold), None)


async def main() -> None:
    questions = json.loads((DIR / "bo-cau-hoi" / "khop_chinh_xac_10.json").read_text(encoding="utf-8"))["câu_hỏi"]
    from_env = next((line.split("=", 1)[1].strip() for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines() if line.startswith("EMBEDDING_ENDPOINT=")), "")
    os.environ["EMBEDDING_ENDPOINT"] = from_env.replace("host.docker.internal", "127.0.0.1")
    settings = get_settings()
    embedding = deps.get_embedding_port(settings)
    engine = create_async_engine(str(settings.database_url).rsplit("/", 1)[0] + "/vsf_bench")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        version = (await session.execute(text("select embedding_model_version from document_chunks limit 1"))).scalar_one()

    methods = ["BM25 riêng", "vector riêng", "RRF mặc định (k=60, 1:1)", "RRF tối ưu (k=10, 0,1:1)", "RRF k=10, 0,5:1", "tối ưu + giữ chỗ BM25"]
    results: dict[str, list[int | None]] = {m: [] for m in methods}
    rows = []
    for item in questions:
        gold = set(item["mục_đúng"])
        vector = (await embedding.embed([item["question"]]))[0]
        async with factory() as session:
            bm25 = await _bm25_search(session, lexical_query=to_lexical_text(item["question"]), as_of=date.today(), model_version=version, top_k=30)
            dense = await _dense_search(session, query_vector=vector, as_of=date.today(), model_version=version, top_k=30)
        optimized = fuse(bm25, dense, 10, 0.1, 1.0)
        orders = {
            "BM25 riêng": bm25_sections(bm25),
            "vector riêng": fuse([], dense, 60, 0.0, 1.0),
            "RRF mặc định (k=60, 1:1)": fuse(bm25, dense, 60, 1.0, 1.0),
            "RRF tối ưu (k=10, 0,1:1)": optimized,
            "RRF k=10, 0,5:1": fuse(bm25, dense, 10, 0.5, 1.0),
        }
        top = optimized[:4]
        for sid in bm25_sections(bm25):
            if sid not in top:
                top.append(sid)
                break
        orders["tối ưu + giữ chỗ BM25"] = top + [s for s in optimized if s not in top]
        line = {"id": item["id"], "câu": item["question"][:52]}
        for method in methods:
            rank = rank_of(orders[method], gold)
            results[method].append(rank)
            line[method] = rank
        rows.append(line)

    def hit(ranks: list[int | None], k: int) -> float:
        return sum(1 for r in ranks if r is not None and r <= k) / len(ranks)

    lines = ["Đo truy hồi trên 10 câu cần khớp đúng chuỗi (không LLM). Số trong bảng đầu là HẠNG của mục đúng (— = ngoài top 30).", "",
             "| Câu | " + " | ".join(methods) + " |", "|---|" + "---|" * len(methods)]
    for row in rows:
        lines.append(f"| {row['id']} {row['câu']} | " + " | ".join("—" if row[m] is None else str(row[m]) for m in methods) + " |")
    lines += ["", "| Cách xếp hạng | Hit@1 | Hit@3 | Hit@5 |", "|---|---|---|---|"]
    for method in methods:
        r = results[method]
        lines.append(f"| {method} | {hit(r, 1):.0%} | {hit(r, 3):.0%} | {hit(r, 5):.0%} |")
    out = DIR / "ket-qua" / "quet-tham-so"
    (out / "khop_chinh_xac.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "khop_chinh_xac.json").write_text(json.dumps({"hạng": rows, "tổng": {m: {"hit1": hit(results[m], 1), "hit3": hit(results[m], 3), "hit5": hit(results[m], 5)} for m in methods}}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(lines))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
