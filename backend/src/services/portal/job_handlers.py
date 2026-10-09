"""Các việc nền của portal: kích hoạt phiên bản tài liệu (có phần trăm theo bước) và tạo task bằng AI.

Kế hoạch: plan-portal/ingest-tai-lieu-va-tao-task-bang-ai.md mục 14.4 (trọng số phần trăm) và 14.5 (tạo task bằng AI).

Phần trăm kích hoạt: kiểm tra 0-5, cắt mục/đoạn 5-20, **embedding 20-80 theo từng lô thật** (tối đa 32 chuỗi), ghi DB
90-99 (một transaction), xong 100. Phiên bản đã có chunk cùng model embedding thì dùng lại, không tốn tiền embedding.
"""

from __future__ import annotations

import asyncio
import contextlib
import tempfile
import time
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from src.infrastructure.ai.chat_completion_port import ChatCompletionPort
from src.infrastructure.ai.deepseek_adapter import ChatCompletionError
from src.infrastructure.observability.call_metrics import call_context
from src.model.document import Document
from src.model.document_chunk import DocumentChunk
from src.model.document_version import DocumentVersion
from src.model.enums import JobKind, VersionStatus
from src.model.llm_call import LlmCall
from src.services.ingest.chunker import ChunkDraft, SectionDraft
from src.services.ingest.embedding.modal_adapter import EmbeddingServiceError
from src.services.ingest.embedding.port import EmbeddingPort
from src.services.ingest.embedding_reuse import find_reusable_vectors
from src.services.ingest.ingest_service import chunk_markdown, today_in
from src.services.ingest.ocr import OcrError
from src.services.ingest.parser import ParseError, parse_document
from src.services.ingest.structure import AiSplit, ai_split_markdown, analyze_structure
from src.services.ingest.version_lifecycle import (
    activate_version_row,
    count_children,
    delete_sections_and_chunks,
    embedding_text_of,
    write_sections_and_chunks,
)
from src.services.portal import ai_task_service
from src.services.portal.errors import PortalError
from src.services.portal.job_service import (
    ClaimedJob,
    JobContext,
    JobFailureError,
    JobHandler,
    JobProgress,
)
from src.services.portal.proposal_progress import DocumentSteps, ProposalTracker

EMBED_BATCH_SIZE = 32
STRUCTURE_OPERATION = "ingest.structure"


async def current_model_version(embedding: EmbeddingPort) -> str:
    """Adapter thật chỉ biết model sau lần gọi đầu tiên (`unknown` trước đó): gọi thử một chuỗi ngắn để lấy."""
    if embedding.model_version in ("", "unknown"):
        with call_context(operation="ingest.probe"):
            await embedding.embed(["kiểm tra"])
    return embedding.model_version


async def _embed_in_batches(
    ctx: JobContext,
    texts: list[str],
    progress: JobProgress,
    *,
    start_percent: float,
    span_percent: float,
    operation: str,
) -> list[list[float]]:
    vectors: list[list[float]] = []
    total = len(texts)
    for offset in range(0, total, EMBED_BATCH_SIZE):
        part = texts[offset : offset + EMBED_BATCH_SIZE]
        try:
            with call_context(operation=operation):
                batch = await ctx.embedding.embed(part)
        except EmbeddingServiceError as exc:
            raise JobFailureError("EMBEDDING_FAILED", f"dịch vụ embedding lỗi: {exc}", retryable=True) from exc
        if len(batch) != len(part) or any(len(vector) != ctx.embedding.dimension for vector in batch):
            raise JobFailureError("EMBEDDING_CONTRACT", "số vector trả về không khớp số đoạn hoặc sai số chiều")
        vectors.extend(batch)
        await progress.update(start_percent + span_percent * len(vectors) / total, f"Embedding {len(vectors)}/{total}")
    return vectors


async def _llm_calls_today(ctx: JobContext, operation: str) -> int:
    start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    async with ctx.session_factory() as session:
        count = await session.scalar(
            select(func.count()).select_from(LlmCall).where(LlmCall.operation == operation, LlmCall.created_at >= start)
        )
    return int(count or 0)


async def _maybe_ai_split(
    ctx: JobContext, markdown: str, quality_report: dict[str, Any], progress: JobProgress
) -> AiSplit | None:
    """Bậc 5 (mục 13.2b): chỉ chạy khi luật cố định thấy cấu trúc vẫn kém, tài liệu đủ dài, chưa thử lần nào và còn hạn mức.

    Mọi lỗi (thiếu khóa, mạng, đề xuất không qua kiểm chứng) đều trả None: kích hoạt vẫn thành công bằng kết quả rule-based.
    """
    structure = quality_report.get("structure") or {}
    if (
        not ctx.structure_llm_enabled
        or structure.get("quality") != "POOR"
        or int(structure.get("word_count", 0)) < ctx.structure_llm_min_words
        or "ai_split" in quality_report
    ):
        return None
    if await _llm_calls_today(ctx, STRUCTURE_OPERATION) >= ctx.structure_llm_daily_limit:
        quality_report["ai_split"] = {"applied": False, "reason": "daily_limit"}
        return None
    try:
        llm = ctx.make_llm()
    except RuntimeError:
        return None
    await progress.update(8, "AI đang chia mục tài liệu")
    with call_context(operation=STRUCTURE_OPERATION):
        split = await ai_split_markdown(markdown, llm)
    if split is None:
        quality_report["ai_split"] = {"applied": False, "reason": "rejected"}
        return None
    await progress.update(18, "Đã chia mục bằng AI")
    return split


async def run_activate_version(ctx: JobContext, claimed: ClaimedJob, progress: JobProgress) -> dict[str, Any]:
    payload = claimed.payload
    version_id = int(payload["version_id"])
    effective_from = date.fromisoformat(str(payload["effective_from"]))
    actor_id = int(payload["actor_id"])
    today = today_in(ctx.timezone)

    await progress.update(2, "Kiểm tra bản kích hoạt")
    async with ctx.session_factory() as session:
        version = await session.get(DocumentVersion, version_id)
        if version is None or version.status != VersionStatus.PROCESSING:
            raise JobFailureError("VERSION_STATE_CHANGED", "phiên bản không còn ở trạng thái chờ kích hoạt")
        markdown = version.markdown
        quality_report = dict(version.quality_report)
        ai_before = quality_report.get("ai_split")
        snapshot_updated_at = version.updated_at
        _, chunk_count = await count_children(session, version_id)
        existing_model = (
            await session.scalar(
                select(DocumentChunk.embedding_model_version).where(DocumentChunk.version_id == version_id).limit(1)
            )
            if chunk_count
            else None
        )
    await progress.update(5, "Đọc cấu trúc tài liệu")

    if ctx.embedding.model_version in ("", "unknown"):
        # Lần gọi đầu có thể chậm (dịch vụ embedding khởi động nguội, đo thật khoảng 18 giây): báo rõ thay vì đứng im ở 5%.
        await progress.update(6, "Kết nối dịch vụ embedding")
    target_model = await current_model_version(ctx.embedding)
    reuse = chunk_count > 0 and existing_model == target_model
    reembed_existing = chunk_count > 0 and not reuse

    chunks_by_section: list[tuple[SectionDraft, list[ChunkDraft]]] = []
    vectors: list[list[float]] = []
    reused_chunks = 0
    ai_info: dict[str, Any] | None = None
    if reuse:
        await progress.update(80, "Dùng lại dữ liệu đã embedding")
    elif reembed_existing:
        # Bản cũ có sẵn section/chunk nhưng embedding bằng model khác: giữ nguyên section/chunk (task có thể đang trỏ
        # vào section này), chỉ tính lại vector.
        async with ctx.session_factory() as session:
            existing_texts = list(
                (
                    await session.scalars(
                        select(DocumentChunk.embedding_text)
                        .where(DocumentChunk.version_id == version_id)
                        .order_by(DocumentChunk.chunk_index)
                    )
                ).all()
            )
        await progress.update(20, "Chuẩn bị embedding lại")
        vectors = await _embed_in_batches(
            ctx, existing_texts, progress, start_percent=20, span_percent=60, operation="ingest.reembed"
        )
    else:
        split = await _maybe_ai_split(ctx, markdown, quality_report, progress)
        if split is not None:
            markdown = split.markdown
        ai_info = (
            quality_report.get("ai_split") if split is None else {"applied": True, "heading_count": len(split.headings)}
        )
        chunks_by_section, all_chunks = await asyncio.to_thread(chunk_markdown, markdown)
        if not all_chunks:
            raise JobFailureError("NO_CHUNKS", "không tách được đoạn nào từ tài liệu (0 đoạn)")
        await progress.update(20, "Đã cắt mục và đoạn")
        texts = [embedding_text_of(chunk) for chunk in all_chunks]
        cached: dict[str, list[float]] = {}
        if ctx.embedding_cache_enabled:
            async with ctx.session_factory() as session:
                cached = await find_reusable_vectors(
                    session, all_chunks, model_version=target_model, dimension=ctx.embedding.dimension
                )
        if not ctx.embedding_cache_enabled:
            vectors = await _embed_in_batches(
                ctx, texts, progress, start_percent=20, span_percent=60, operation="ingest.embed"
            )
        else:
            # Chỉ tính các đoạn chưa có vector cùng model (đoạn trùng nhau trong cùng tài liệu cũng chỉ tính một lần).
            missing = list(dict.fromkeys(text for text in texts if text not in cached))
            reused_chunks = sum(1 for text in texts if text in cached)
            if cached:
                await progress.update(22, f"Dùng lại {reused_chunks}/{len(texts)} đoạn đã embedding")
            computed = await _embed_in_batches(
                ctx, missing, progress, start_percent=22, span_percent=58, operation="ingest.embed"
            )
            fresh = dict(zip(missing, computed, strict=True))
            vectors = [cached[text] if text in cached else fresh[text] for text in texts]

    await progress.update(90, "Đang ghi dữ liệu")
    section_count = len(chunks_by_section)
    async with ctx.session_factory() as session:
        locked = await session.scalar(select(DocumentVersion).where(DocumentVersion.id == version_id).with_for_update())
        if locked is None or locked.status != VersionStatus.PROCESSING or locked.updated_at != snapshot_updated_at:
            raise JobFailureError("VERSION_CHANGED", "phiên bản đã bị thay đổi trong lúc xử lý")
        if reembed_existing:
            chunks = list(
                (
                    await session.scalars(
                        select(DocumentChunk)
                        .where(DocumentChunk.version_id == version_id)
                        .order_by(DocumentChunk.chunk_index)
                    )
                ).all()
            )
            for chunk, vector in zip(chunks, vectors, strict=True):
                chunk.embedding = vector
                chunk.embedding_model_version = target_model
        elif not reuse:
            await delete_sections_and_chunks(session, version_id)
            await write_sections_and_chunks(
                session,
                version=locked,
                chunks_by_section=chunks_by_section,
                vectors=vectors,
                embedding_model_version=target_model,
            )
        locked.embedding_model_version = target_model
        if ai_info is not None and ai_info != ai_before:
            # Ghi lại kết quả bước AI chia mục: Markdown mới (đã có heading) và nhãn để giao diện hiện "AI đề xuất".
            _, structure = analyze_structure(markdown, infer=False)
            locked.markdown = markdown
            locked.quality_report = {**locked.quality_report, "ai_split": ai_info, "structure": structure.as_dict()}
        try:
            closed = await activate_version_row(
                session, version=locked, effective_from=effective_from, actor_id=actor_id, today=today
            )
            sections, chunks_total = await count_children(session, version_id)
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise JobFailureError("ACTIVATION_CONFLICT", "hiệu lực mới chồng ngày với một bản đang áp dụng") from exc
    return {
        "version_id": version_id,
        "section_count": sections or section_count,
        "chunk_count": chunks_total,
        "closed_version_ids": closed,
        "reused_embeddings": reuse,
        "reused_chunks": reused_chunks,
    }


async def cleanup_activate_version(ctx: JobContext, claimed: ClaimedJob, message: str) -> None:
    """Kích hoạt hỏng hẳn: trả phiên bản về trạng thái trước đó (DB tài liệu vẫn nguyên) và ghi lý do để hiện cho HR."""
    version_id = int(claimed.payload["version_id"])
    previous = str(claimed.payload.get("previous_status") or VersionStatus.DRAFT.value)
    async with ctx.session_factory() as session:
        version = await session.get(DocumentVersion, version_id)
        if version is not None and version.status == VersionStatus.PROCESSING:
            version.status = previous
            version.failure_reason = message[:500]
            await session.commit()


async def run_ingest_version(ctx: JobContext, claimed: ClaimedJob, progress: JobProgress) -> dict[str, Any]:
    """Bản nháp từ PDF scan: OCR để có lớp chữ, đọc thành Markdown, rồi mở khóa bản nháp (PROCESSING -> DRAFT)."""
    version_id = int(claimed.payload["version_id"])
    if ctx.read_file is None or ctx.ocr_pdf is None:
        raise JobFailureError("OCR_DISABLED", "OCR chưa được bật trên máy chủ")
    async with ctx.session_factory() as session:
        version = await session.get(DocumentVersion, version_id)
        if version is None or version.status != VersionStatus.PROCESSING:
            raise JobFailureError("VERSION_STATE_CHANGED", "phiên bản không còn ở trạng thái chờ OCR")
        storage_key, filename = version.storage_key, version.original_filename
    await progress.update(5, "Đọc file scan")
    try:
        pdf = await ctx.read_file(storage_key)
    except Exception as exc:
        raise JobFailureError("FILE_UNREADABLE", "không đọc lại được file đã tải lên", retryable=True) from exc
    await progress.update(10, "Đang nhận dạng chữ (OCR)")
    started = time.perf_counter()
    try:
        searchable = await ctx.ocr_pdf(pdf)
    except OcrError as exc:
        raise JobFailureError("OCR_FAILED", f"OCR không thành công: {exc}") from exc
    elapsed = round(time.perf_counter() - started, 1)
    await progress.update(85, "Đọc văn bản sau OCR")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(searchable)
        path = Path(tmp.name)
    try:
        parsed = await asyncio.to_thread(parse_document, path)
    except ParseError as exc:
        raise JobFailureError("OCR_EMPTY", "OCR không đọc được chữ nào trong file") from exc
    finally:
        path.unlink(missing_ok=True)
    try:
        new_key = await ctx.storage.store(searchable, checksum=parsed.file_checksum, filename=filename)
    except Exception as exc:
        raise JobFailureError("STORAGE_FAILED", "không lưu được file sau OCR", retryable=True) from exc
    structured, structure = analyze_structure(parsed.markdown)
    async with ctx.session_factory() as session:
        locked = await session.scalar(select(DocumentVersion).where(DocumentVersion.id == version_id).with_for_update())
        if locked is None or locked.status != VersionStatus.PROCESSING:
            raise JobFailureError("VERSION_CHANGED", "phiên bản đã bị thay đổi trong lúc OCR")
        locked.markdown = structured
        locked.content_checksum = parsed.content_checksum
        locked.storage_key = new_key
        locked.file_checksum = parsed.file_checksum
        locked.size_bytes = parsed.size_bytes
        locked.parser = "markitdown+ocr"
        locked.quality_report = {
            "structure": structure.as_dict(),
            "has_embedded_images": parsed.has_embedded_images,
            "ocr": {"engine": "tesseract", "seconds": elapsed},
        }
        locked.failure_reason = None
        locked.status = VersionStatus.DRAFT.value
        await session.commit()
    return {"version_id": version_id, "characters": len(structured), "ocr_seconds": elapsed}


async def cleanup_ingest_version(ctx: JobContext, claimed: ClaimedJob, message: str) -> None:
    """OCR hỏng hẳn: trả bản nháp về DRAFT (trống) kèm lý do để HR thấy và xóa được."""
    version_id = int(claimed.payload["version_id"])
    async with ctx.session_factory() as session:
        version = await session.get(DocumentVersion, version_id)
        if version is not None and version.status == VersionStatus.PROCESSING:
            version.status = VersionStatus.DRAFT.value
            version.failure_reason = message[:500]
            await session.commit()


async def _document_title(ctx: JobContext, version_id: int) -> tuple[str, str]:
    async with ctx.session_factory() as session:
        row = (
            await session.execute(
                select(Document.title, DocumentVersion.version_label)
                .join(DocumentVersion, DocumentVersion.document_id == Document.id)
                .where(DocumentVersion.id == version_id)
            )
        ).one_or_none()
    return (row[0], row[1]) if row else ("(không rõ)", "")


async def _propose_for_document(
    ctx: JobContext, llm: ChatCompletionPort, version_id: int, steps: DocumentSteps
) -> dict[str, Any]:
    """Đề xuất task cho MỘT tài liệu; lỗi biết trước (JSON hỏng, AI không gọi được) chỉ làm hỏng tài liệu đó, không hỏng cả job."""
    started = time.perf_counter()
    entry: dict[str, Any] = {
        "version_id": version_id,
        "document_title": steps.title,
        "version_label": steps.version_label,
    }
    try:
        async with ctx.session_factory() as session:
            detailed = await ai_task_service.propose_tasks_detailed(
                session, document_version_id=version_id, llm=llm, options=ctx.proposal, progress=steps
            )
        entry["status"] = "DONE"
        entry["proposals"] = [proposal.model_dump() for proposal in detailed.proposals]
        entry["truncated_sections"] = detailed.truncated
        entry["uncovered_sections"] = [
            {"section_id": item.section_id, "heading": item.heading} for item in detailed.uncovered
        ]
        # Số liệu của lượt chạy (không có nội dung): để HR/dev biết task được xếp bởi AI hay theo thứ tự tài liệu, và mỗi bước mất bao lâu.
        entry["skipped_info_sections"] = [
            {"section_id": item.section_id, "heading": item.heading} for item in detailed.skipped_info
        ]
        entry["metrics"] = {
            "mode": ctx.proposal.mode,
            "order_source": detailed.order_source,
            "batches": detailed.batches,
            "skipped_sections": len(detailed.skipped_info),
            "seconds": {**detailed.timings, "total": round(time.perf_counter() - started, 2)},
        }
    except PortalError as error:
        entry.update(status="FAILED", error=error.code, proposals=[])
        steps.failed = True
    except ChatCompletionError:
        entry.update(status="FAILED", error="LLM_UNAVAILABLE", proposals=[])
        steps.failed = True
    finally:
        steps.finish_all()
    return entry


async def run_ai_task_proposal(ctx: JobContext, claimed: ClaimedJob, progress: JobProgress) -> dict[str, Any]:
    """Tạo task bằng AI cho các tài liệu đã chọn. Các tài liệu chạy SONG SONG (bị giới hạn chung bởi `LlmGate`), tiến độ theo
    bước thật gom thành một thanh (`ProposalTracker`)."""
    version_ids = [int(value) for value in claimed.payload.get("version_ids", [])]
    if not version_ids:
        raise JobFailureError("NO_DOCUMENTS", "chưa chọn tài liệu nào")
    try:
        llm = ctx.make_llm()
    except RuntimeError as exc:
        raise JobFailureError("LLM_NOT_CONFIGURED", "chưa cấu hình dịch vụ AI") from exc

    info = [await _document_title(ctx, version_id) for version_id in version_ids]
    tracker = ProposalTracker(progress, [(v, title) for v, (title, _) in zip(version_ids, info, strict=True)])
    for steps, (_, label) in zip(tracker.documents, info, strict=True):
        steps.version_label = label
    ticker = asyncio.create_task(tracker.run_ticker())
    try:
        outcomes = await asyncio.gather(
            *(
                _propose_for_document(ctx, llm, version_id, steps)
                for version_id, steps in zip(version_ids, tracker.documents, strict=True)
            ),
            return_exceptions=True,
        )
    finally:
        ticker.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await ticker
    for outcome in outcomes:
        if isinstance(outcome, BaseException):
            raise outcome  # lỗi không lường trước: để `_run_claimed_job` ghi nhận
    documents = [outcome for outcome in outcomes if isinstance(outcome, dict)]

    # Mọi tài liệu đều không gọi được AI: nhiều khả năng lỗi tạm (quá tải, mất mạng) nên thử lại một lần trước khi báo thất bại.
    if all(entry.get("error") == "LLM_UNAVAILABLE" for entry in documents) and claimed.attempts < claimed.max_attempts:
        raise JobFailureError("LLM_UNAVAILABLE", "dịch vụ AI tạm thời không phản hồi", retryable=True)
    await tracker.saving()
    await tracker.saved()
    return {"documents": documents}


HANDLERS: dict[str, JobHandler] = {
    JobKind.ACTIVATE_VERSION.value: JobHandler(run=run_activate_version, on_final_failure=cleanup_activate_version),
    JobKind.AI_TASK_PROPOSAL.value: JobHandler(run=run_ai_task_proposal),
    JobKind.INGEST_VERSION.value: JobHandler(run=run_ingest_version, on_final_failure=cleanup_ingest_version),
}

__all__ = ["HANDLERS", "current_model_version", "run_activate_version", "run_ai_task_proposal"]
