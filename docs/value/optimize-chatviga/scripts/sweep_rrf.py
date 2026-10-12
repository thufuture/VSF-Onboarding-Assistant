"""Quét tham số RRF (chỉ truy hồi, KHÔNG gọi LLM) trên tập "chỉnh" 70 câu.

Với mỗi câu có đáp án mục chuẩn: chạy hai nhánh BM25 và vector MỘT lần (câu gốc, không qua bước viết lại bằng LLM), lưu thứ hạng,
rồi thử nhiều cách trộn trên cùng danh sách: RRF với k ∈ {10, 30, 60, 100} × hệ số (BM25 : vector) ∈ {0,1 ; 0,25 ; 0,5 ; 1 ; 2},
cùng hai mốc đối chứng (chỉ BM25, chỉ vector). Không ghi gì vào DB. Đo Hit@1/3/5, MRR, Recall@5, Recall@10, Recall tất cả.
Ghi cả danh sách ứng viên theo từng câu vào `ket-qua/quet-tham-so/ung_vien_70.json` để bước quét rerank dùng lại.

Chạy từ gốc repo:
  PYTHONIOENCODING=utf-8 PYTHONPATH=backend backend/.venv/Scripts/python.exe docs/value/optimize-chatviga/scripts/sweep_rrf.py
"""

import asyncio
import json
import os
import statistics
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

GOLDEN = DIR / "bo-cau-hoi" / "golden_v0_nhap.jsonl"
OUT = DIR / "ket-qua" / "quet-tham-so"
KS = (10, 30, 60, 100)
WEIGHTS = ((0.1, 1.0), (0.25, 1.0), (0.5, 1.0), (1.0, 1.0), (2.0, 1.0))  # (hệ số BM25, hệ số vector)


def gold_sets(item: dict) -> list[set[int]]:
    sets: list[set[int]] = []
    contexts = item.get("contexts_expected") or []
    acceptable = item.get("contexts_acceptable") or []
    for index, context in enumerate(contexts):
        if not isinstance(context, dict):
            continue
        ids = {context["section_id"], *context.get("tương_đương_section_id", [])}
        if index < len(acceptable):
            ids |= {a["section_id"] for a in acceptable[index]}
        sets.append(ids)
    return sets


def fuse(bm25: list[tuple[int, int]], dense: list[tuple[int, int]], k: int, w_bm25: float, w_dense: float) -> list[int]:
    """Trả về danh sách section_id sắp theo điểm RRF có trọng số; điểm section = điểm cao nhất của các chunk con."""
    section_of = dict(bm25) | dict(dense)
    scores: dict[int, float] = {}
    for rank, (chunk_id, _) in enumerate(bm25, 1):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + w_bm25 / (k + rank)
    for rank, (chunk_id, _) in enumerate(dense, 1):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + w_dense / (k + rank)
    best: dict[int, float] = {}
    for chunk_id, score in scores.items():
        section_id = section_of[chunk_id]
        best[section_id] = max(best.get(section_id, 0.0), score)
    return sorted(best, key=lambda s: -best[s])


def metrics(ranked: list[int], golds: list[set[int]]) -> dict[str, float]:
    def rank_of(gold: set[int]) -> int | None:
        return next((i + 1 for i, sid in enumerate(ranked) if sid in gold), None)

    ranks = [rank_of(g) for g in golds]
    n = len(golds)
    return {
        "hit1": sum(r is not None and r <= 1 for r in ranks) / n,
        "hit3": sum(r is not None and r <= 3 for r in ranks) / n,
        "hit5": sum(r is not None and r <= 5 for r in ranks) / n,
        "mrr": sum((1 / r) if r else 0.0 for r in ranks) / n,
        "recall5": sum(r is not None and r <= 5 for r in ranks) / n,
        "recall10": sum(r is not None and r <= 10 for r in ranks) / n,
        "recall_all": sum(r is not None for r in ranks) / n,
    }


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    from_env = next(
        (line.split("=", 1)[1].strip() for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines() if line.startswith("EMBEDDING_ENDPOINT=")), ""
    )
    os.environ["EMBEDDING_ENDPOINT"] = os.environ.get("BENCH_EMBEDDING_ENDPOINT") or from_env.replace("host.docker.internal", "127.0.0.1")
    settings = get_settings()
    embedding = deps.get_embedding_port(settings)
    engine = create_async_engine(str(settings.database_url).rsplit("/", 1)[0] + "/vsf_bench")
    factory = async_sessionmaker(engine, expire_on_commit=False)

    tune_ids = set(json.loads((DIR / "bo-cau-hoi" / "tap_chinh_70.json").read_text(encoding="utf-8"))["id"])
    items = [json.loads(line) for line in GOLDEN.read_text(encoding="utf-8").splitlines()]
    todo = [i for i in items if i["id"] in tune_ids and gold_sets(i) and i.get("route_kỳ_vọng") == "document" and i.get("loại_phản_hồi") == "ANSWER"]
    print(f"{len(todo)} câu tài liệu có đáp án trong tập chỉnh", flush=True)

    async with factory() as session:
        version = (await session.execute(text("select embedding_model_version from document_chunks limit 1"))).scalar_one()

    candidates: dict[str, dict] = {}
    for number, item in enumerate(todo, 1):
        question = item["question"]
        vector = (await embedding.embed([question]))[0]
        async with factory() as session:
            bm25 = await _bm25_search(session, lexical_query=to_lexical_text(question), as_of=date.today(), model_version=version, top_k=30)
            dense = await _dense_search(session, query_vector=vector, as_of=date.today(), model_version=version, top_k=30)
        candidates[item["id"]] = {"bm25": bm25, "dense": dense}
        if number % 10 == 0:
            print(f"  đã tìm {number}/{len(todo)}", flush=True)
    (OUT / "ung_vien_70.json").write_text(json.dumps(candidates), encoding="utf-8")

    configs: list[tuple[str, int | None, float, float]] = [("chỉ BM25", 60, 1.0, 0.0), ("chỉ vector", 60, 0.0, 1.0)]
    for k in KS:
        for w_bm25, w_dense in WEIGHTS:
            configs.append((f"RRF k={k}, BM25:vector={w_bm25:g}:{w_dense:g}", k, w_bm25, w_dense))

    rows = []
    for name, k, w_bm25, w_dense in configs:
        per_question = {}
        for item in todo:
            c = candidates[item["id"]]
            ranked = fuse([tuple(x) for x in c["bm25"]], [tuple(x) for x in c["dense"]], k or 60, w_bm25, w_dense)
            per_question[item["id"]] = metrics(ranked, gold_sets(item))
        mean = {key: statistics.mean(m[key] for m in per_question.values()) for key in next(iter(per_question.values()))}
        rows.append({"cấu_hình": name, "k": k, "w_bm25": w_bm25, "w_vector": w_dense, "trung_bình": mean, "theo_câu": per_question})

    baseline = next(r for r in rows if r["k"] == 60 and r["w_bm25"] == 1.0 and r["w_vector"] == 1.0)
    best = max(rows, key=lambda r: (r["trung_bình"]["hit1"] + r["trung_bình"]["mrr"], r["trung_bình"]["recall10"]))
    summary = {"số_câu": len(todo), "mặc_định": baseline["cấu_hình"], "tốt_nhất": best["cấu_hình"], "cấu_hình": rows}
    (OUT / "rrf.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")

    lines = [f"Quét RRF trên {len(todo)} câu tài liệu có đáp án (tập chỉnh), câu gốc, không LLM.", "", "| Cấu hình | Hit@1 | Hit@3 | Hit@5 | MRR | Recall@5 | Recall@10 | Recall tất cả |", "|---|---|---|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: -(r["trung_bình"]["hit1"] + r["trung_bình"]["mrr"])):
        m = r["trung_bình"]
        mark = " (mặc định hiện tại)" if r is baseline else (" (tốt nhất)" if r is best else "")
        lines.append(f"| {r['cấu_hình']}{mark} | {m['hit1']:.1%} | {m['hit3']:.1%} | {m['hit5']:.1%} | {m['mrr']:.3f} | {m['recall5']:.1%} | {m['recall10']:.1%} | {m['recall_all']:.1%} |")
    (OUT / "rrf.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
