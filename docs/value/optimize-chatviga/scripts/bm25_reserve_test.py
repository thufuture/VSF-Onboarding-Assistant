"""Đo tác dụng của "giữ chỗ BM25" (chỉ truy hồi, KHÔNG gọi LLM), dùng đúng hàm `select_with_bm25_reserve` của sản phẩm.

Hai bộ: (a) 49 câu ngữ nghĩa của tập chỉnh (ứng viên đã lưu ở ket-qua/quet-tham-so/ung_vien_70.json), (b) 18 câu khớp đúng chuỗi
(bo-cau-hoi/khop_chinh_xac_10.json, truy vấn trực tiếp vào `vsf_bench`). Với mỗi số mục giữ lại N ∈ {5, 3, 2} so: không giữ chỗ,
giữ 1 chỗ, (N=5) giữ 2 chỗ. Chỉ số: "có mặt" = mục đúng nằm trong N mục giữ lại; Hit@1 = mục đúng đứng đầu danh sách giữ lại.
Danh sách giữ lại: các mục RRF (k=10, BM25:vector = 0,1:1) rồi đến mục BM25 được giữ chỗ (nằm cuối).

Chạy từ gốc repo:
  PYTHONIOENCODING=utf-8 PYTHONPATH=backend backend/.venv/Scripts/python.exe docs/value/optimize-chatviga/scripts/bm25_reserve_test.py
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
from src.services.retrieval.hybrid_search import _bm25_search, _dense_search, select_with_bm25_reserve  # noqa: E402
from sweep_rrf import GOLDEN, OUT, fuse, gold_sets  # noqa: E402

SETTINGS_GRID = [(5, 0), (5, 1), (5, 2), (3, 0), (3, 1), (2, 0), (2, 1)]


def evaluate(cases: list[tuple[list[set[int]], list[tuple[int, int]], list[tuple[int, int]]]]) -> dict[tuple[int, int], dict[str, float]]:
    out: dict[tuple[int, int], dict[str, float]] = {}
    for n, reserve in SETTINGS_GRID:
        present = hit1 = total = 0
        for golds, bm25, dense in cases:
            ordered = fuse(bm25, dense, 10, 0.1, 1.0)
            bm25_sections = list(dict.fromkeys(section for _, section in bm25))
            kept = select_with_bm25_reserve(ordered, bm25_sections, n, reserve)
            for gold in golds:
                total += 1
                present += any(sid in gold for sid in kept)
                hit1 += bool(kept) and kept[0] in gold
        out[(n, reserve)] = {"có_mặt": present / total, "hit1": hit1 / total}
    return out


async def main() -> None:
    items = {json.loads(line)["id"]: json.loads(line) for line in GOLDEN.read_text(encoding="utf-8").splitlines()}
    cand = json.loads((OUT / "ung_vien_70.json").read_text(encoding="utf-8"))
    semantic = [([g for g in gold_sets(items[i])], [tuple(x) for x in c["bm25"]], [tuple(x) for x in c["dense"]]) for i, c in cand.items()]

    from_env = next((line.split("=", 1)[1].strip() for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines() if line.startswith("EMBEDDING_ENDPOINT=")), "")
    os.environ["EMBEDDING_ENDPOINT"] = from_env.replace("host.docker.internal", "127.0.0.1")
    settings = get_settings()
    embedding = deps.get_embedding_port(settings)
    engine = create_async_engine(str(settings.database_url).rsplit("/", 1)[0] + "/vsf_bench")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        version = (await session.execute(text("select embedding_model_version from document_chunks limit 1"))).scalar_one()
    exact = []
    for item in json.loads((DIR / "bo-cau-hoi" / "khop_chinh_xac_10.json").read_text(encoding="utf-8"))["câu_hỏi"]:
        vector = (await embedding.embed([item["question"]]))[0]
        async with factory() as session:
            bm25 = await _bm25_search(session, lexical_query=to_lexical_text(item["question"]), as_of=date.today(), model_version=version, top_k=30)
            dense = await _dense_search(session, query_vector=vector, as_of=date.today(), model_version=version, top_k=30)
        exact.append(([set(item["mục_đúng"])], bm25, dense))
    await engine.dispose()

    sem, exa = evaluate(semantic), evaluate(exact)
    lines = [f"Giữ chỗ BM25 (chỉ truy hồi). Bộ ngữ nghĩa: {len(semantic)} câu; bộ khớp chuỗi: {len(exact)} câu.", "",
             "| Giữ N mục | Chỗ BM25 | Ngữ nghĩa: có mặt | Ngữ nghĩa: Hit@1 | Khớp chuỗi: có mặt | Khớp chuỗi: Hit@1 |", "|---|---|---|---|---|---|"]
    for key in SETTINGS_GRID:
        n, reserve = key
        lines.append(f"| {n} | {reserve} | {sem[key]['có_mặt']:.1%} | {sem[key]['hit1']:.1%} | {exa[key]['có_mặt']:.1%} | {exa[key]['hit1']:.1%} |")
    (OUT / "giu_cho_bm25.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT / "giu_cho_bm25.json").write_text(json.dumps({"ngữ_nghĩa": {f"{k[0]}_{k[1]}": v for k, v in sem.items()}, "khớp_chuỗi": {f"{k[0]}_{k[1]}": v for k, v in exa.items()}}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    asyncio.run(main())
