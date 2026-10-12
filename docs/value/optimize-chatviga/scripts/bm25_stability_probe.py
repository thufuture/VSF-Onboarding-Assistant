"""Thử độ ổn định của truy vấn BM25 (ParadeDB `pg_search`) với đúng hàm của sản phẩm, trên DB bench và DB dev.

Mục đích: lần chạy benchmark thấy ~8% câu lỗi `unrecognized node type` (chập chờn) và `could not parse query string` (câu có dấu ngoặc).
Probe gọi `_bm25_search` lặp lại với các câu hỏi thật của golden set, tuần tự rồi song song (đúng kiểu pipeline: mỗi câu hỏi con một session),
đếm lỗi theo loại. Chỉ ĐỌC; không ghi gì.

Chạy từ gốc repo: PYTHONIOENCODING=utf-8 PYTHONPATH=backend backend/.venv/Scripts/python.exe docs/value/optimize-chatviga/scripts/bm25_stability_probe.py
"""

import asyncio
import collections
import json
import random
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from src.config import get_settings  # noqa: E402
from src.services.ingest.lexical import to_lexical_text  # noqa: E402
from src.services.retrieval.hybrid_search import _bm25_search  # noqa: E402

GOLDEN = ROOT / "docs" / "value" / "optimize-chatviga" / "bo-cau-hoi" / "golden_v0_nhap.jsonl"


def kind(exc: Exception) -> str:
    message = str(exc)
    if "unrecognized node type" in message:
        return "unrecognized node type"
    if "could not parse query string" in message:
        return "could not parse query string"
    return f"{type(exc).__name__}: {message[:80]}"


async def probe(database: str, queries: list[str], parallel: int, rounds: int, statement_cache: bool) -> dict[str, int]:
    settings = get_settings()
    url = str(settings.database_url).rsplit("/", 1)[0] + "/" + database
    connect_args = {} if statement_cache else {"statement_cache_size": 0}
    engine = create_async_engine(url, connect_args=connect_args)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        version = (await session.execute(text("select embedding_model_version from document_chunks limit 1"))).scalar_one()
    counts: collections.Counter[str] = collections.Counter()

    async def one(query: str) -> None:
        async with factory() as session:
            try:
                await _bm25_search(session, lexical_query=to_lexical_text(query), as_of=date.today(), model_version=version, top_k=30)
                counts["ok"] += 1
            except Exception as exc:  # noqa: BLE001
                counts[kind(exc)] += 1

    rng = random.Random(7)
    for _ in range(rounds):
        batch = [rng.choice(queries) for _ in range(parallel)]
        await asyncio.gather(*(one(q) for q in batch))
    await engine.dispose()
    return dict(counts)


async def main() -> None:
    questions = [json.loads(line)["question"] for line in GOLDEN.read_text(encoding="utf-8").splitlines()]
    # chỉ các câu KHÔNG có ký tự đặc biệt cú pháp, để tách lỗi chập chờn khỏi lỗi cú pháp cố định
    clean = [q for q in questions if not any(c in q for c in '[]{}()"~^*:\\')]
    print(f"{len(clean)}/{len(questions)} câu không có ký tự đặc biệt")
    for database in ("vsf_bench", "vsf"):
        for parallel, rounds, cache in ((1, 150, True), (3, 60, True), (3, 60, False)):
            result = await probe(database, clean, parallel, rounds, cache)
            print(f"{database:10s} song song={parallel} bộ đệm câu lệnh={'bật' if cache else 'tắt'}: {result}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
