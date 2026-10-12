"""Harness chạy golden set qua Viga THẬT (cùng mã sản phẩm, không sửa) trên DB riêng `vsf_bench` (bản chụp DB dev).

Mỗi câu chạy tuần tự (để đo độ trễ sạch) qua `ask_viga`, ghi: kết quả Viga, công cụ/định tuyến, các mục truy hồi theo từng câu con,
thời gian từng bước (router, rewrite, embed, truy hồi, trả lời, kiểm trích dẫn), token và chi phí từng lệnh LLM (nối bằng `collect_calls`).
Không ghi gì vào DB dev. Các cấu hình thử (rerank, ...) được cắm bằng monkeypatch tại đây, KHÔNG sửa mã sản phẩm.

Chạy từ gốc repo:
  PYTHONIOENCODING=utf-8 PYTHONPATH=backend backend/.venv/Scripts/python.exe docs/value/optimize-chatviga/scripts/run_viga_benchmark.py \
      --label R0_dry --sample 10 --runs 1
"""

import argparse
import contextvars
import hashlib
import asyncio
import dataclasses
import json
import os
import statistics
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "backend"))

import httpx  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from src.api import dependencies as deps  # noqa: E402
from src.config import get_settings  # noqa: E402
from src.infrastructure.observability.call_metrics import collect_calls, set_prices  # noqa: E402
from src.infrastructure.observability.langfuse_tracer import LangfuseTracer  # noqa: E402
from src.model.user import User  # noqa: E402
from src.services.retrieval import hybrid_search  # noqa: E402
from src.services.viga import pipeline, service  # noqa: E402

DIR = Path(__file__).resolve().parents[1]
GOLDEN = DIR / "bo-cau-hoi" / "golden_v0_nhap.jsonl"
PERSONA_EMAIL = "newhire3@vsf-demo.example"

EVENTS: list[dict[str, Any]] = []  # sự kiện của câu đang chạy (chạy tuần tự nên dùng danh sách chung)
RERANK: dict[str, Any] = {"enabled": False, "url": "http://127.0.0.1:8090/rerank", "top": 20, "keep": 5, "query": "lexical", "max_len": 512, "timeout": None, "fallbacks": 0}  # cấu hình R1 đặt qua tham số dòng lệnh
FUSION: dict[str, Any] = {"enabled": False, "k": 60, "w_bm25": 1.0, "w_vector": 1.0}  # RRF có trọng số (chỉ trong harness)
CURRENT_QUESTION: contextvars.ContextVar[str] = contextvars.ContextVar("current_question", default="")  # câu hỏi con dạng tự nhiên
RERANK_CACHE_PATH = DIR / "ket-qua" / "rerank_cache_chay.json"
RERANK_CACHE: dict[str, float] = {}


def timed(name: str, function: Any) -> Any:
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        try:
            return await function(*args, **kwargs)
        finally:
            EVENTS.append({"bước": name, "giây": round(time.perf_counter() - started, 3)})

    return wrapper


def install_probes(embedding: Any) -> None:
    """Gắn bộ đo vào các bước của pipeline (chỉ ghi nhận, không đổi hành vi)."""
    pipeline.rewrite_query = timed("rewrite", pipeline.rewrite_query)
    pipeline.answer_with_claims = timed("trả_lời", pipeline.answer_with_claims)
    original_validate = pipeline.validate_claims

    def validate(*args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        out = original_validate(*args, **kwargs)
        EVENTS.append({"bước": "kiểm_trích_dẫn", "giây": round(time.perf_counter() - started, 3)})
        return out

    pipeline.validate_claims = validate
    if FUSION["enabled"]:
        def weighted_rrf(*ranked_lists: list[int], k: int = FUSION["k"], weights: tuple[float, ...] | None = None) -> dict[int, float]:  # noqa: ARG001 - harness dùng FUSION
            weights = (FUSION["w_bm25"], FUSION["w_vector"])
            scores: dict[int, float] = {}
            for weight, ranked in zip(weights, ranked_lists, strict=True):
                for rank, item_id in enumerate(ranked, start=1):
                    scores[item_id] = scores.get(item_id, 0.0) + weight / (FUSION["k"] + rank)
            return scores

        hybrid_search.reciprocal_rank_fusion = weighted_rrf
    original_evidence = pipeline._evidence_for_question

    async def evidence_with_question(session_factory: Any, *, question: str, **kwargs: Any) -> Any:
        CURRENT_QUESTION.set(question)  # mỗi câu hỏi con chạy trong một task riêng nên không lẫn nhau
        return await original_evidence(session_factory, question=question, **kwargs)

    pipeline._evidence_for_question = evidence_with_question
    original_search = pipeline.search_to_sections

    async def search(session: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        sections = await original_search(session, **kwargs)
        EVENTS.append(
            {
                "bước": "truy_hồi",
                "giây": round(time.perf_counter() - started, 3),
                "câu_con": kwargs.get("lexical_query"),
                "mục": [{"section_id": s.section_id, "heading": s.heading, "token": s.token_count, "điểm": round(s.score, 5), "tài_liệu": s.document_title} for s in sections],
            }
        )
        return sections

    async def search_with_rerank(session: Any, **kwargs: Any) -> Any:
        """Cấu hình R1: lấy tối đa RERANK_TOP ứng viên (bỏ ngân sách token), chấm lại bằng cross-encoder, giữ RERANK_KEEP mục tốt nhất trong ngân sách."""
        started = time.perf_counter()
        saved_budget = hybrid_search.SECTION_TOKEN_BUDGET
        hybrid_search.SECTION_TOKEN_BUDGET = 10**9
        try:
            candidates = await original_search(session, **kwargs)
        finally:
            hybrid_search.SECTION_TOKEN_BUDGET = saved_budget
        search_seconds = time.perf_counter() - started
        candidates = candidates[:RERANK["top"]]
        rerank_started = time.perf_counter()
        scores: list[float] = []
        fell_back = False
        if len(candidates) > 1:
            natural = CURRENT_QUESTION.get()
            query = natural if RERANK["query"] == "natural" and natural else kwargs.get("lexical_query", "")
            passages = [f"{s.heading}\n{s.content}" for s in candidates]
            keys = [hashlib.sha1(f"{RERANK['max_len']}\x00{query}\x00{p}".encode()).hexdigest() for p in passages]
            missing = [i for i, key in enumerate(keys) if key not in RERANK_CACHE]
            if missing:  # điểm của một cặp không đổi giữa các lần chạy: nhớ lại để các ô cùng cấu hình truy hồi không chấm lại

                async def call() -> None:
                    async with httpx.AsyncClient(timeout=600) as client:
                        response = await client.post(RERANK["url"], json={"query": query, "passages": [passages[i] for i in missing], "max_length": RERANK["max_len"]})
                        response.raise_for_status()
                        for i, score in zip(missing, response.json()["scores"], strict=True):
                            RERANK_CACHE[keys[i]] = score

                try:
                    await asyncio.wait_for(call(), timeout=RERANK["timeout"])  # hạn cứng: quá hạn thì dùng thứ tự RRF
                except asyncio.TimeoutError:
                    fell_back = True
                    RERANK["fallbacks"] += 1
            scores = [-float(i) for i in range(len(candidates))] if fell_back else [RERANK_CACHE[key] for key in keys]
        else:
            scores = [0.0] * len(candidates)
        rerank_seconds = time.perf_counter() - rerank_started
        ranked = sorted(zip(candidates, scores, strict=True), key=lambda pair: -pair[1])
        kept: list[Any] = []
        total_tokens = 0
        for evidence, score in ranked[: RERANK["keep"]]:
            if total_tokens + evidence.token_count > saved_budget and kept:
                break
            kept.append(dataclasses.replace(evidence, score=float(score)))
            total_tokens += evidence.token_count
        EVENTS.append(
            {
                "bước": "truy_hồi",
                "giây": round(time.perf_counter() - started, 3),
                "giây_tìm": round(search_seconds, 3),
                "giây_rerank": round(rerank_seconds, 3),
                "rerank_rơi_về_rrf": fell_back,
                "câu_con": kwargs.get("lexical_query"),
                "mục_trước_rerank": [{"section_id": s.section_id, "heading": s.heading, "token": s.token_count, "điểm": round(s.score, 5)} for s in candidates],
                "mục": [{"section_id": s.section_id, "heading": s.heading, "token": s.token_count, "điểm": round(s.score, 5), "tài_liệu": s.document_title} for s in kept],
            }
        )
        return kept

    pipeline.search_to_sections = search_with_rerank if RERANK["enabled"] else search
    original_embed = embedding.embed

    async def embed(texts: list[str]) -> Any:
        started = time.perf_counter()
        try:
            return await original_embed(texts)
        finally:
            EVENTS.append({"bước": "embed", "giây": round(time.perf_counter() - started, 3), "số_chuỗi": len(texts)})

    embedding.embed = embed
    service.route_question = timed_route(service.route_question)
    service.run_tool = record_tool(service.run_tool)


def timed_route(function: Any) -> Any:
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        decision = await function(*args, **kwargs)
        EVENTS.append(
            {
                "bước": "router",
                "giây": round(time.perf_counter() - started, 3),
                "quyết_định": None if decision is None else {"tool": decision.tool, "độ_tin_cậy": decision.confidence, "hỏi_lại": bool(decision.clarify), "tham_số": decision.args},
            }
        )
        return decision

    return wrapper


def record_tool(function: Any) -> Any:
    def wrapper(name: str, snapshot: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        reply = function(name, snapshot, **kwargs)
        EVENTS.append({"bước": "công_cụ", "tên": name, "giây": round(time.perf_counter() - started, 4), "tham_số": kwargs.get("args")})
        return reply

    return wrapper


def load_items(path: Path) -> list[dict]:
    """Đọc golden (.jsonl) hoặc bộ an toàn (.json) về cùng một dạng: id, question, category, tập."""
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    document = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for q in document["câu_hỏi"]:
        if q.get("cần_harness_hỗ_trợ"):
            continue  # cần dựng bối cảnh (lịch sử/nội dung task bị đầu độc): chưa chạy được ở bản đầu
        out.append({**q, "question": q["câu_hỏi"], "category": f"{q['bộ']} / {q['nhóm']}", "tập": "all"})
    return out


def pick(items: list[dict], split: str, sample: int | None, ids: list[str] | None) -> list[dict]:
    chosen = [i for i in items if split == "all" or i["tập"] == split]
    if ids:
        return [i for i in chosen if i["id"] in ids]
    if sample:
        buckets: dict[str, list[dict]] = {}
        for item in chosen:
            buckets.setdefault(item["category"], []).append(item)
        out: list[dict] = []
        while len(out) < sample and any(buckets.values()):
            for key in list(buckets):
                if buckets[key] and len(out) < sample:
                    out.append(buckets[key].pop(0))
        return out
    return chosen


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--split", default="all", choices=["dev", "phát triển", "đóng băng", "all"])
    parser.add_argument("--sample", type=int, default=None, help="lấy N câu đa dạng nhóm (để chạy thử)")
    parser.add_argument("--ids", default=None, help="danh sách id, cách nhau dấu phẩy")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--rerank", action="store_true", help="cấu hình R1: rerank bằng bge-reranker-v2-m3 (cần dịch vụ run_reranker.sh)")
    parser.add_argument("--rerank-top", type=int, default=20, help="số ứng viên đưa vào reranker")
    parser.add_argument("--rerank-keep", type=int, default=5, help="số mục giữ lại sau rerank")
    parser.add_argument("--rerank-query", default="lexical", choices=["lexical", "natural"], help="câu hỏi đưa cho reranker: đã tách từ (cũ) hoặc câu hỏi con gốc")
    parser.add_argument("--rerank-timeout", type=float, default=None, help="hạn cứng (giây) cho mỗi lần rerank; quá hạn thì dùng thứ tự RRF")
    parser.add_argument("--rerank-max-len", type=int, default=512, help="độ dài tối đa mỗi cặp (token)")
    parser.add_argument("--rrf-k", type=float, default=None, help="RRF k (bật RRF có trọng số khi đặt)")
    parser.add_argument("--w-bm25", type=float, default=1.0, help="hệ số nhánh BM25")
    parser.add_argument("--w-vector", type=float, default=1.0, help="hệ số nhánh vector")
    parser.add_argument("--ids-file", default=None, help="tệp JSON có khóa 'id' (danh sách câu hỏi cần chạy)")
    parser.add_argument("--golden", default=str(GOLDEN), help="tệp câu hỏi (.jsonl golden hoặc .json bộ an toàn)")
    parser.add_argument("--start-run", type=int, default=1, help="số thứ tự lượt bắt đầu (để chạy xen kẽ các cấu hình)")
    args = parser.parse_args()
    RERANK.update(enabled=args.rerank, top=args.rerank_top, keep=args.rerank_keep, query=args.rerank_query, max_len=args.rerank_max_len, timeout=args.rerank_timeout)
    if args.rrf_k is not None:
        FUSION.update(enabled=True, k=args.rrf_k, w_bm25=args.w_bm25, w_vector=args.w_vector)
    if RERANK_CACHE_PATH.exists():
        RERANK_CACHE.update(json.loads(RERANK_CACHE_PATH.read_text(encoding="utf-8")))
    split = "phát triển" if args.split == "dev" else args.split

    # Embedding: dùng đúng endpoint trong .env như Viga dev thật. Dev đặt `host.docker.internal` (chỉ phân giải được TRONG container);
    # harness chạy trên máy host nên đổi sang 127.0.0.1 (cùng một embedder local, cùng khóa). Ghi đè bằng BENCH_EMBEDDING_ENDPOINT nếu cần.
    configured = os.environ.get("BENCH_EMBEDDING_ENDPOINT")
    if configured:
        os.environ["EMBEDDING_ENDPOINT"] = configured
    else:
        from_env = next((line.split("=", 1)[1].strip() for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines() if line.startswith("EMBEDDING_ENDPOINT=")), "")
        os.environ["EMBEDDING_ENDPOINT"] = from_env.replace("host.docker.internal", "127.0.0.1")
    settings = get_settings()
    # App thật nạp bảng giá lúc khởi động; không nạp thì chi phí mỗi lệnh luôn là 0.
    set_prices(
        llm_input_per_million=settings.llm_price_input_per_million_usd,
        llm_output_per_million=settings.llm_price_output_per_million_usd,
        embedding_per_second=settings.embedding_price_per_second_usd,
    )
    url = str(settings.database_url).rsplit("/", 1)[0] + "/vsf_bench"
    engine = create_async_engine(url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    embedding = deps.get_embedding_port(settings)
    install_probes(embedding)
    tracer = LangfuseTracer(enabled=False, public_key=None, secret_key=None, host=None)

    async with session_factory() as session:
        user = (await session.execute(select(User).where(User.email == PERSONA_EMAIL))).scalar_one()

    items = load_items(Path(args.golden))
    wanted_ids = args.ids.split(",") if args.ids else (json.loads(Path(args.ids_file).read_text(encoding="utf-8"))["id"] if args.ids_file else None)
    todo = pick(items, split, args.sample, wanted_ids)
    out_dir = DIR / "ket-qua" / args.label
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[{args.label}] {len(todo)} câu × {args.runs} lượt | DB bench | mô hình {settings.llm_model}", flush=True)

    for run in range(args.start_run, args.start_run + args.runs):
        lines: list[str] = []
        for number, item in enumerate(todo, 1):
            EVENTS.clear()
            started = time.perf_counter()
            error = None
            result = None
            with collect_calls() as used:
                try:
                    result = await service.ask_viga(
                        user=user,
                        question=item["question"],
                        conversation_id=None,
                        session_factory=session_factory,
                        embedding=embedding,
                        make_llm=lambda: deps.get_chat_completion_port(settings),
                        tracer=tracer,
                        today=date.today(),
                    )
                except Exception as exc:  # ghi lại lỗi, không dừng cả lượt chạy
                    error = f"{type(exc).__name__}: {str(exc)[:160]}"
            wall = time.perf_counter() - started
            calls = [
                {
                    "thao_tác": c.operation, "mô_hình": c.model, "giây": round(c.latency_ms / 1000, 3), "token_vào": c.prompt_tokens, "token_ra": c.completion_tokens,
                    "token_suy_luận": c.reasoning_tokens, "token_cache": c.cached_input_tokens, "chi_phí_usd": round(c.cost_usd, 6), "ok": c.ok, "lần_thử": c.attempt, "chờ_hàng_đợi_ms": c.queue_wait_ms,
                }
                for c in used.calls
                if c.kind == "llm"
            ]
            record = {
                "id": item["id"], "lượt": run, "nhãn": args.label, "câu_hỏi": item["question"], "lỗi": error, "tổng_giây": round(wall, 3),
                "kết_quả": None if result is None else {
                    "loại": result.response_type, "route": result.route, "khóa_tin_nhắn": result.message_key, "nội_dung": result.message[:600],
                    "claims": [{"câu_con": c.question, "loại": c.response_type, "trả_lời": c.text, "trích_dẫn": c.quote, "nguồn": None if c.source is None else {"tài_liệu": c.source.document_title, "mục": c.source.section_heading, "version_id": c.source.version_id}} for c in result.claims],
                    "chưa_trả_lời": result.unanswered, "việc_bị_chặn": len(result.blocking_tasks), "hành_động": [vars(a) for a in result.actions][:3], "có_thể_báo_HR": result.can_report,
                },
                "sự_kiện": list(EVENTS), "lệnh_LLM": calls,
                "chi_phí_usd": round(sum(c["chi_phí_usd"] for c in calls), 6), "token_vào": sum(c["token_vào"] for c in calls), "token_ra": sum(c["token_ra"] for c in calls),
            }
            lines.append(json.dumps(record, ensure_ascii=False, default=str))
            if RERANK["enabled"]:
                RERANK_CACHE_PATH.write_text(json.dumps(RERANK_CACHE), encoding="utf-8")
            kind = "-" if result is None else result.response_type
            print(f"  [{number}/{len(todo)}] {item['id']} {kind:<12} {wall:5.1f}s ${record['chi_phí_usd']:.4f} {item['question'][:55]}", flush=True)
        (out_dir / f"lượt_{run}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        walls = [json.loads(line)["tổng_giây"] for line in lines]
        costs = [json.loads(line)["chi_phí_usd"] for line in lines]
        errors = sum(1 for line in lines if json.loads(line)["lỗi"])
        walls_sorted = sorted(walls)
        print(f"lượt {run}: p50 {statistics.median(walls):.2f}s | p95 {walls_sorted[min(len(walls_sorted) - 1, int(0.95 * len(walls_sorted)))]:.2f}s | chi phí LLM tổng ${sum(costs):.4f} (${sum(costs) / max(1, len(costs)):.4f}/câu) | lỗi {errors}", flush=True)
    await engine.dispose()


if __name__ == "__main__":
    hybrid_search  # noqa: B018  (giữ import để dễ gắn cấu hình rerank sau này)
    asyncio.run(main())
