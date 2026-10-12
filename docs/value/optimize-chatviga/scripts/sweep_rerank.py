"""Quét tham số rerank trên tập "chỉnh" (chỉ truy hồi, KHÔNG gọi LLM). Cần dịch vụ run_reranker.sh đang chạy.

Lấy 20 ứng viên đầu của cấu hình RRF tốt nhất (từ rrf.json), chấm bằng bge-reranker-v2-m3 với ba biến thể rồi so thứ hạng sau rerank:
  lexical_512 : câu hỏi đã tách từ (như harness cũ)      , 512 token
  natural_512 : câu hỏi gốc                              , 512 token
  natural_256 : câu hỏi gốc                              , 256 token
Điểm của 12 ứng viên đầu lấy từ chính điểm của 20 (cặp độc lập nên điểm giống hệt chấm riêng). Điểm được nhớ lại để chạy lại không tốn thời gian.

Chạy từ gốc repo:
  PYTHONIOENCODING=utf-8 PYTHONPATH=backend backend/.venv/Scripts/python.exe docs/value/optimize-chatviga/scripts/sweep_rerank.py
"""

import asyncio
import hashlib
import json
import os
import statistics
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[4]
DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(DIR / "scripts"))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from src.config import get_settings  # noqa: E402
from src.services.ingest.lexical import to_lexical_text  # noqa: E402
from sweep_rrf import GOLDEN, OUT, fuse, gold_sets, metrics  # noqa: E402

URL = "http://127.0.0.1:8090/rerank"
TAG = os.environ.get("SWEEP_TAG", "")  # ví dụ "_int8": tách tệp nhớ điểm và tệp kết quả khỏi lần quét gốc
TOP = int(os.environ.get("SWEEP_TOP", "20"))
CACHE_PATH = OUT / f"rerank_cache{TAG}.json"
ALL_VARIANTS = (("lexical_512", "lexical", 512), ("natural_512", "natural", 512), ("natural_256", "natural", 256), ("lexical_256", "lexical", 256))
WANTED = os.environ.get("SWEEP_VARIANTS", "lexical_512,natural_512,natural_256").split(",")
VARIANTS = tuple(v for v in ALL_VARIANTS if v[0] in WANTED)


def key(query: str, passage: str, max_len: int) -> str:
    return hashlib.sha1(f"{max_len}\x00{query}\x00{passage}".encode()).hexdigest()


async def main() -> None:
    rrf = json.loads((OUT / "rrf.json").read_text(encoding="utf-8"))
    best = next(r for r in rrf["cấu_hình"] if r["cấu_hình"] == rrf["tốt_nhất"])
    chosen = next((r for r in rrf["cấu_hình"] if r["k"] == 10 and r["w_bm25"] == 0.1), best)  # giữ nhánh BM25 nhẹ để còn "hybrid"
    k, w_bm25, w_vector = chosen["k"] or 60, chosen["w_bm25"], chosen["w_vector"]
    print(f"nền RRF: {chosen['cấu_hình']}", flush=True)

    candidates = json.loads((OUT / "ung_vien_70.json").read_text(encoding="utf-8"))
    items = {json.loads(line)["id"]: json.loads(line) for line in GOLDEN.read_text(encoding="utf-8").splitlines()}
    cache: dict[str, float] = json.loads(CACHE_PATH.read_text(encoding="utf-8")) if CACHE_PATH.exists() else {}

    settings = get_settings()
    engine = create_async_engine(str(settings.database_url).rsplit("/", 1)[0] + "/vsf_bench")
    factory = async_sessionmaker(engine, expire_on_commit=False)

    per_variant: dict[str, dict[str, dict]] = {name: {} for name, _, _ in VARIANTS}
    baseline: dict[str, dict] = {}
    seconds: dict[str, list[float]] = {name: [] for name, _, _ in VARIANTS}
    pairs_total: dict[str, int] = {name: 0 for name, _, _ in VARIANTS}

    async with httpx.AsyncClient(timeout=600) as client:
        for number, (item_id, cand) in enumerate(candidates.items(), 1):
            item = items[item_id]
            question = item["question"]
            ranked = fuse([tuple(x) for x in cand["bm25"]], [tuple(x) for x in cand["dense"]], k, w_bm25, w_vector)[:TOP]
            async with factory() as session:
                rows = (await session.execute(text("select id, heading, content from document_sections where id = any(:ids)"), {"ids": ranked})).all()
            by_id = {r.id: f"{r.heading}\n{r.content}" for r in rows}
            ranked = [sid for sid in ranked if sid in by_id]
            golds = gold_sets(item)
            baseline[item_id] = {"top20": metrics(ranked, golds), "top12": metrics(ranked[:12], golds)}
            for name, form, max_len in VARIANTS:
                query = to_lexical_text(question) if form == "lexical" else question
                passages = [by_id[sid] for sid in ranked]
                need = [i for i, p in enumerate(passages) if key(query, p, max_len) not in cache]
                if need:
                    response = await client.post(URL, json={"query": query, "passages": [passages[i] for i in need], "max_length": max_len})
                    response.raise_for_status()
                    body = response.json()
                    for i, score in zip(need, body["scores"], strict=True):
                        cache[key(query, passages[i], max_len)] = score
                    seconds[name].append(body["seconds"])
                    pairs_total[name] += len(need)
                scores = [cache[key(query, p, max_len)] for p in passages]
                order20 = [sid for _, sid in sorted(zip(scores, ranked, strict=True), key=lambda t: -t[0])]
                top12 = list(zip(scores[:12], ranked[:12], strict=True))
                order12 = [sid for _, sid in sorted(top12, key=lambda t: -t[0])]
                per_variant[name][item_id] = {"top20": metrics(order20, golds), "top12": metrics(order12, golds)}
            if number % 5 == 0:
                CACHE_PATH.write_text(json.dumps(cache), encoding="utf-8")
                print(f"  {number}/{len(candidates)} câu", flush=True)
    CACHE_PATH.write_text(json.dumps(cache), encoding="utf-8")

    def mean(table: dict[str, dict], slot: str) -> dict[str, float]:
        keys = next(iter(table.values()))[slot].keys()
        return {m: statistics.mean(v[slot][m] for v in table.values()) for m in keys}

    rows_out = [{"cấu_hình": "chỉ RRF (không rerank), 12 ứng viên", "trung_bình": mean(baseline, "top12")}]
    if TOP >= 20:
        rows_out.insert(0, {"cấu_hình": "chỉ RRF (không rerank), 20 ứng viên", "trung_bình": mean(baseline, "top20")})
    for name, _, _ in VARIANTS:
        sec_per_pair = (sum(seconds[name]) / pairs_total[name]) if pairs_total[name] else None
        for slot, size in ((("top20", 20), ("top12", 12)) if TOP >= 20 else (("top12", 12),)):
            rows_out.append(
                {
                    "cấu_hình": f"rerank {name}, {size} ứng viên",
                    "trung_bình": mean(per_variant[name], slot),
                    "giây_mỗi_cặp": sec_per_pair,
                    "giây_mỗi_câu_hỏi": None if sec_per_pair is None else round(sec_per_pair * size, 2),
                }
            )
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"rerank{TAG}.json").write_text(json.dumps({"nền_rrf": chosen["cấu_hình"], "số_câu": len(candidates), "cấu_hình": rows_out}, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [f"Quét rerank trên {len(candidates)} câu (tập chỉnh). Nền: {chosen['cấu_hình']}. Thời gian đo ở máy dev với dịch vụ rerank hiện chạy.", "", "| Cấu hình | Hit@1 | Hit@3 | Hit@5 | MRR | Recall@5 | giây/cặp | giây/câu hỏi |", "|---|---|---|---|---|---|---|---|"]
    for r in rows_out:
        m = r["trung_bình"]
        spp = r.get("giây_mỗi_cặp")
        lines.append(f"| {r['cấu_hình']} | {m['hit1']:.1%} | {m['hit3']:.1%} | {m['hit5']:.1%} | {m['mrr']:.3f} | {m['recall5']:.1%} | {'' if spp is None else f'{spp:.2f}'} | {r.get('giây_mỗi_câu_hỏi') or ''} |")
    (OUT / f"rerank{TAG}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
