"""Hàng đợi việc nền bằng PostgreSQL (bảng `jobs`) và worker chạy trong tiến trình backend.

Kế hoạch: plan-portal/ingest-tai-lieu-va-tao-task-bang-ai.md mục 14. Không thêm hạ tầng mới (không Redis/Celery):
worker lấy việc bằng `FOR UPDATE SKIP LOCKED`, nên chạy nhiều tiến trình cũng không lấy trùng một job.

Nguyên tắc:
- Tiến độ và lỗi nằm trong `jobs`, **không chứa nội dung tài liệu** (INV8); dữ liệu tài liệu chỉ ghi ở bước cuối trong
  một transaction nên job lỗi thì DB tài liệu vẫn sạch.
- Chống chạy chồng: `idempotency_key` + chỉ mục duy nhất trên job PENDING/RUNNING (INV10).
- Job treo (worker chết): `locked_at` cũ quá `job_stale_seconds` thì đưa về hàng đợi, hết lượt thì FAILED.
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
import uuid
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.infrastructure.ai.chat_completion_port import ChatCompletionPort
from src.infrastructure.observability.call_metrics import call_context
from src.infrastructure.observability.langfuse_tracer import current_tracer
from src.model.enums import JobStatus, UserRole
from src.model.job import Job
from src.model.user import User
from src.services.ingest.embedding.port import EmbeddingPort
from src.services.ingest.storage import StoragePort
from src.services.portal.errors import PortalError
from src.services.portal.proposal_options import ProposalOptions

logger = logging.getLogger(__name__)

ERROR_MAX_LENGTH = 300


class JobFailureError(Exception):
    """Handler báo lỗi có mã rõ ràng. `retryable=True` thì được chạy lại nếu còn lượt (`max_attempts`)."""

    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


@dataclass(frozen=True)
class JobContext:
    """Những thứ handler cần để làm việc; dựng một lần ở lifespan (hoặc ở test với adapter giả)."""

    session_factory: async_sessionmaker[AsyncSession]
    embedding: EmbeddingPort
    storage: StoragePort
    make_llm: Callable[[], ChatCompletionPort]
    timezone: str = "Asia/Ho_Chi_Minh"
    structure_llm_enabled: bool = True
    structure_llm_min_words: int = 400
    structure_llm_daily_limit: int = 30
    # Dùng lại vector của đoạn không đổi so với các phiên bản khác (mặc định tắt, bật bằng EMBEDDING_CACHE_ENABLED).
    embedding_cache_enabled: bool = False
    # Cách đề xuất task bằng AI (đường nhanh/cũ, kích thước lô, giờ chờ mỗi lời gọi).
    proposal: ProposalOptions = field(default_factory=ProposalOptions)


@dataclass(frozen=True)
class ClaimedJob:
    id: int
    kind: str
    payload: dict[str, Any]
    created_by: int | None
    document_version_id: int | None
    attempts: int
    max_attempts: int


class JobProgress:
    """Báo tiến độ (đơn điệu tăng, tối đa 99; 100 chỉ khi job xong). Mỗi lần báo cũng là nhịp sống của job."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession], job_id: int) -> None:
        self._factory = session_factory
        self._job_id = job_id
        self._last = 0

    async def update(self, percent: float, stage: str, steps: dict[str, Any] | None = None) -> None:
        """`steps` (tùy chọn) là tiến độ theo bước, ghi vào `jobs.progress` để giao diện vẽ danh sách bước."""
        value = max(self._last, min(99, int(percent)))
        self._last = value
        values: dict[str, Any] = {"progress_percent": value, "stage": stage[:96], "locked_at": func.now()}
        if steps is not None:
            values["progress"] = steps
        async with self._factory() as session:
            await session.execute(update(Job).where(Job.id == self._job_id).values(**values))
            await session.commit()


HEARTBEAT_SECONDS = 15.0


async def _heartbeat(session_factory: async_sessionmaker[AsyncSession], job_id: int, interval: float) -> None:
    """Nhịp sống riêng của job, không phụ thuộc handler có báo tiến độ hay không (một lời gọi LLM dài không bị coi là worker chết)."""
    while True:
        await asyncio.sleep(interval)
        try:
            async with session_factory() as session:
                await session.execute(update(Job).where(Job.id == job_id).values(locked_at=func.now()))
                await session.commit()
        except Exception:
            logger.exception("job_heartbeat_failed job_id=%s", job_id)


HandlerRun = Callable[[JobContext, ClaimedJob, JobProgress], Awaitable[dict[str, Any] | None]]
HandlerCleanup = Callable[[JobContext, ClaimedJob, str], Awaitable[None]]


@dataclass(frozen=True)
class JobHandler:
    run: HandlerRun
    # Gọi khi job hỏng hẳn (hết lượt hoặc lỗi không thử lại được): trả dữ liệu về trạng thái trước khi chạy.
    on_final_failure: HandlerCleanup | None = None


Handlers = Mapping[str, JobHandler]


async def enqueue_job(
    session: AsyncSession,
    *,
    kind: str,
    payload: dict[str, Any],
    idempotency_key: str,
    created_by: int | None,
    document_version_id: int | None = None,
    max_attempts: int = 2,
) -> Job:
    """Tạo job; nếu đã có job PENDING/RUNNING cùng `idempotency_key` thì trả lại job đó (bấm hai lần không chạy chồng)."""
    existing = await _active_job_by_key(session, idempotency_key)
    if existing is not None:
        return existing
    job = Job(
        kind=kind,
        payload=payload,
        idempotency_key=idempotency_key,
        created_by=created_by,
        document_version_id=document_version_id,
        max_attempts=max_attempts,
        stage="Đang chờ",
    )
    session.add(job)
    try:
        await session.commit()
    except IntegrityError:
        # Hai request cùng lúc: chỉ mục duy nhất giữ một job, request thua lấy lại job của request thắng.
        await session.rollback()
        existing = await _active_job_by_key(session, idempotency_key)
        if existing is None:
            raise
        return existing
    return job


async def _active_job_by_key(session: AsyncSession, key: str) -> Job | None:
    job: Job | None = await session.scalar(
        select(Job).where(
            Job.idempotency_key == key,
            Job.status.in_([JobStatus.PENDING.value, JobStatus.RUNNING.value]),
        )
    )
    return job


async def claim_next_job(session_factory: async_sessionmaker[AsyncSession], worker_id: str) -> ClaimedJob | None:
    async with session_factory() as session:
        job = await session.scalar(
            select(Job)
            .where(Job.status == JobStatus.PENDING.value, Job.run_after <= func.now())
            .order_by(Job.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if job is None:
            return None
        now = datetime.now(UTC)
        job.status = JobStatus.RUNNING.value
        job.attempts += 1
        job.locked_by = worker_id
        job.locked_at = now
        job.started_at = job.started_at or now
        job.progress_percent = 0
        job.progress = None
        job.stage = "Đang bắt đầu"
        await session.commit()
        return ClaimedJob(
            id=job.id,
            kind=job.kind,
            payload=dict(job.payload),
            created_by=job.created_by,
            document_version_id=job.document_version_id,
            attempts=job.attempts,
            max_attempts=job.max_attempts,
        )


async def _finish_success(
    session_factory: async_sessionmaker[AsyncSession], job_id: int, result: dict[str, Any] | None
) -> None:
    async with session_factory() as session:
        await session.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(
                status=JobStatus.SUCCEEDED.value,
                progress_percent=100,
                stage="Hoàn tất",
                result=result,
                last_error=None,
                finished_at=func.now(),
                locked_by=None,
            )
        )
        await session.commit()


async def _finish_failure(
    ctx: JobContext, handlers: Handlers, claimed: ClaimedJob, *, code: str, message: str, retryable: bool
) -> None:
    text = f"{code}: {message}"[:ERROR_MAX_LENGTH]
    will_retry = retryable and claimed.attempts < claimed.max_attempts
    async with ctx.session_factory() as session:
        if will_retry:
            backoff = 5 * claimed.attempts
            await session.execute(
                update(Job)
                .where(Job.id == claimed.id)
                .values(
                    status=JobStatus.PENDING.value,
                    last_error=text,
                    stage="Chờ chạy lại",
                    run_after=datetime.now(UTC) + timedelta(seconds=backoff),
                    locked_by=None,
                )
            )
        else:
            await session.execute(
                update(Job)
                .where(Job.id == claimed.id)
                .values(
                    status=JobStatus.FAILED.value,
                    last_error=text,
                    stage="Lỗi",
                    finished_at=func.now(),
                    locked_by=None,
                )
            )
        await session.commit()
    if not will_retry:
        handler = handlers.get(claimed.kind)
        if handler is not None and handler.on_final_failure is not None:
            try:
                await handler.on_final_failure(ctx, claimed, text)
            except Exception:
                logger.exception("job_cleanup_failed job_id=%s kind=%s", claimed.id, claimed.kind)


async def requeue_stale_jobs(ctx: JobContext, handlers: Handlers, stale_seconds: int) -> int:
    """Đưa job RUNNING mất nhịp sống về hàng đợi (còn lượt) hoặc FAILED (hết lượt). Trả số job đã xử lý."""
    cutoff = datetime.now(UTC) - timedelta(seconds=stale_seconds)
    async with ctx.session_factory() as session:
        rows = (
            await session.scalars(
                select(Job)
                .where(Job.status == JobStatus.RUNNING.value, Job.locked_at < cutoff)
                .with_for_update(skip_locked=True)
            )
        ).all()
        stale = [
            ClaimedJob(j.id, j.kind, dict(j.payload), j.created_by, j.document_version_id, j.attempts, j.max_attempts)
            for j in rows
        ]
        await session.commit()
    for claimed in stale:
        await _finish_failure(
            ctx, handlers, claimed, code="JOB_INTERRUPTED", message="tiến trình xử lý bị gián đoạn", retryable=True
        )
    return len(stale)


async def process_next_job(ctx: JobContext, handlers: Handlers, worker_id: str) -> bool:
    """Lấy và chạy một job. Trả `False` nếu hàng đợi trống."""
    claimed = await claim_next_job(ctx.session_factory, worker_id)
    if claimed is None:
        return False
    await _run_claimed_job(ctx, handlers, claimed)
    return True


async def run_pending_jobs(ctx: JobContext, handlers: Handlers, *, max_jobs: int = 50) -> int:
    """Chạy lần lượt cho tới khi hàng đợi trống (dùng trong test và lệnh quản trị)."""
    worker_id = f"inline-{uuid.uuid4().hex[:8]}"
    done = 0
    while done < max_jobs and await process_next_job(ctx, handlers, worker_id):
        done += 1
    return done


@dataclass
class JobWorker:
    """Vòng lặp nền trong tiến trình backend: lấy job, chạy tối đa `max_concurrent` job cùng lúc."""

    ctx: JobContext
    handlers: Handlers
    max_concurrent: int = 2
    poll_seconds: float = 1.0
    stale_seconds: int = 300
    # Việc định kỳ (giây giữa hai lần, hàm chạy): vd. xóa hội thoại quá hạn lưu. Lỗi một việc không dừng worker.
    periodic: list[tuple[float, Callable[[], Awaitable[None]]]] = field(default_factory=list)
    _task: asyncio.Task[None] | None = field(default=None, init=False, repr=False)
    _running: set[asyncio.Task[None]] = field(default_factory=set, init=False, repr=False)
    _worker_id: str = field(default_factory=lambda: f"{socket.gethostname()}-{os.getpid()}", init=False)

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._loop(), name="job-worker")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
        for task in list(self._running):
            task.cancel()
        await asyncio.gather(*self._running, return_exceptions=True)
        self._running.clear()

    async def _loop(self) -> None:
        last_sweep = 0.0
        last_periodic = [0.0] * len(self.periodic)
        loop = asyncio.get_running_loop()
        while True:
            try:
                for index, (interval, action) in enumerate(self.periodic):
                    if last_periodic[index] == 0.0 or loop.time() - last_periodic[index] > interval:
                        last_periodic[index] = loop.time()
                        try:
                            await action()
                        except Exception:
                            logger.exception("job_worker_periodic_failed")
                if loop.time() - last_sweep > 30:
                    last_sweep = loop.time()
                    await requeue_stale_jobs(self.ctx, self.handlers, self.stale_seconds)
                started = False
                while len(self._running) < self.max_concurrent:
                    claimed = await claim_next_job(self.ctx.session_factory, self._worker_id)
                    if claimed is None:
                        break
                    started = True
                    task = asyncio.create_task(self._run_claimed(claimed))
                    self._running.add(task)
                    task.add_done_callback(self._running.discard)
                if not started:
                    await asyncio.sleep(self.poll_seconds)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("job_worker_loop_error")
                await asyncio.sleep(self.poll_seconds * 5)

    async def _run_claimed(self, claimed: ClaimedJob) -> None:
        await _run_claimed_job(self.ctx, self.handlers, claimed)


async def _run_claimed_job(ctx: JobContext, handlers: Handlers, claimed: ClaimedJob) -> None:
    handler = handlers.get(claimed.kind)
    if handler is None:
        await _finish_failure(
            ctx,
            handlers,
            claimed,
            code="UNKNOWN_JOB_KIND",
            message=f"không có handler cho {claimed.kind}",
            retryable=False,
        )
        return
    progress = JobProgress(ctx.session_factory, claimed.id)
    beat = asyncio.create_task(_heartbeat(ctx.session_factory, claimed.id, HEARTBEAT_SECONDS))
    try:
        # Gắn người tạo và mã job vào mọi lời gọi LLM/embedding của việc này: cộng được chi phí và độ trễ theo từng lượt.
        with (
            call_context(operation="job", user_id=claimed.created_by, job_id=claimed.id),
            current_tracer().span(
                f"job.{claimed.kind}",
                input={"job_id": claimed.id, "kind": claimed.kind, "payload": claimed.payload},
                user_id=claimed.created_by,
                session_id=f"job-{claimed.id}",
                tags=["job", str(claimed.kind)],
            ) as root,
        ):
            result = await handler.run(ctx, claimed, progress)
            root.update(output=result)
    except asyncio.CancelledError:
        # Tắt backend giữa chừng: để job RUNNING, lần khởi động sau `requeue_stale_jobs` sẽ nhận lại.
        raise
    except JobFailureError as failure:
        await _finish_failure(
            ctx, handlers, claimed, code=failure.code, message=failure.message, retryable=failure.retryable
        )
    except PortalError as error:
        await _finish_failure(ctx, handlers, claimed, code=error.code, message=error.message_key, retryable=False)
    except Exception as exc:
        logger.exception("job_failed job_id=%s kind=%s", claimed.id, claimed.kind)
        await _finish_failure(ctx, handlers, claimed, code="JOB_ERROR", message=type(exc).__name__, retryable=False)
    else:
        await _finish_success(ctx.session_factory, claimed.id, result)
    finally:
        beat.cancel()
        await asyncio.gather(beat, return_exceptions=True)


# --- Đọc job cho API (quyền: người tạo hoặc ADMIN) ---


async def get_job_for_user(session: AsyncSession, job_id: int, user: User) -> Job:
    job = await session.get(Job, job_id)
    # Không phân biệt "không có" với "không phải của bạn" để không lộ sự tồn tại của job người khác.
    if job is None or (user.role != UserRole.ADMIN and job.created_by != user.id):
        raise PortalError(404, "JOB_NOT_FOUND", "portal.job_not_found")
    return job


async def queue_ahead(session: AsyncSession, job: Job) -> int | None:
    """Số job đang chờ xếp trước job này (chỉ có nghĩa khi job còn PENDING) — giao diện hiện "đang xếp hàng, trước bạn còn N việc"."""
    if job.status != JobStatus.PENDING.value:
        return None
    count = await session.scalar(
        select(func.count()).select_from(Job).where(Job.status == JobStatus.PENDING.value, Job.id < job.id)
    )
    return int(count or 0)


async def list_jobs_for_user(
    session: AsyncSession, user: User, *, active_only: bool, kind: str | None = None, limit: int = 50
) -> list[Job]:
    query = select(Job).order_by(Job.id.desc()).limit(limit)
    if user.role != UserRole.ADMIN:
        query = query.where(Job.created_by == user.id)
    if active_only:
        query = query.where(Job.status.in_([JobStatus.PENDING.value, JobStatus.RUNNING.value]))
    if kind is not None:
        query = query.where(Job.kind == kind)
    return list((await session.scalars(query)).all())
