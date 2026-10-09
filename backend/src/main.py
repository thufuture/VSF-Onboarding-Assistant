"""Điểm vào ứng dụng: lifespan (engine DB), middleware X-Request-ID, đăng ký router."""

import logging
import re
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse

from src.api import dependencies as deps
from src.api.routers.admin_router import router as admin_router
from src.api.routers.analytics_router import router as analytics_router
from src.api.routers.auth_router import router as auth_router
from src.api.routers.chat_router import router as chat_router
from src.api.routers.health_router import router as health_router
from src.api.routers.portal_document_router import router as portal_document_router
from src.api.routers.portal_editor_router import router as portal_editor_router
from src.api.routers.portal_router import router as portal_router
from src.api.routers.portal_version_router import router as portal_version_router
from src.api.routers.ticket_router import router as ticket_router
from src.api.routers.viga_router import router as viga_router
from src.config import Settings, get_settings
from src.infrastructure.ai.deepseek_adapter import ChatCompletionError
from src.infrastructure.observability.call_metrics import set_observer, set_prices, set_request_id, set_sink
from src.infrastructure.observability.langfuse_tracer import LangfuseTracer, set_current_tracer
from src.infrastructure.persistence.engine import create_engine, create_session_factory
from src.services.auth.errors import AuthError
from src.services.auth.login_throttle import LoginThrottle
from src.services.auth.seed import assert_no_dev_accounts
from src.services.ingest.embedding.keep_warm import KeepWarm
from src.services.ingest.embedding.modal_adapter import EmbeddingServiceError, ModalEmbeddingAdapter
from src.services.portal.errors import PortalError
from src.services.portal.job_handlers import HANDLERS
from src.services.portal.job_service import JobContext, JobWorker
from src.services.portal.metrics_service import DbCallSink
from src.services.portal.proposal_options import ProposalOptions
from src.services.viga import conversations
from src.services.viga.chat_throttle import ChatThrottle

logger = logging.getLogger(__name__)

# Chỉ nhận ID từ client nếu đơn giản và ngắn; nếu không thì tự tạo (tránh chèn ký tự lạ vào log/header).
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    # Đo từng lần gọi LLM/embedding (thời gian, token, chi phí ước tính) vào bảng llm_calls; không lưu nội dung.
    call_sink = DbCallSink(app.state.session_factory)
    set_sink(call_sink)
    set_prices(
        llm_input_per_million=settings.llm_price_input_per_million_usd,
        llm_output_per_million=settings.llm_price_output_per_million_usd,
        embedding_per_second=settings.embedding_price_per_second_usd,
    )
    worker = _build_job_worker(app, settings)
    if worker is not None:
        worker.start()
    try:
        if settings.app_env == "production":
            # Mật khẩu dev nằm trong repo: production không được chạy khi còn tài khoản dev.
            async with app.state.session_factory() as session:
                await assert_no_dev_accounts(session)
        yield
    finally:
        if worker is not None:
            await worker.stop()
        await call_sink.drain()
        set_sink(None)
        set_observer(None)
        app.state.langfuse_tracer.flush()
        set_current_tracer(None)
        await engine.dispose()


def _build_job_worker(app: FastAPI, settings: Settings) -> JobWorker | None:
    """Worker việc nền (kích hoạt tài liệu, tạo task bằng AI). Thiếu cấu hình embedding thì không chạy, chỉ cảnh báo."""
    if not settings.job_worker_enabled:
        return None

    def resolve(dependency: Callable[..., Any]) -> Callable[..., Any]:
        # Dùng cùng nơi dựng adapter với router (kể cả bản ghi đè ở test), nên worker và request luôn đồng bộ.
        return app.dependency_overrides.get(dependency, dependency)

    try:
        embedding = resolve(deps.get_embedding_port)(settings)
        storage = resolve(deps.get_storage_port)(settings)
    except ValueError:
        logger.warning("job_worker_disabled reason=embedding_or_storage_not_configured")
        return None
    ctx = JobContext(
        session_factory=app.state.session_factory,
        embedding=embedding,
        storage=storage,
        make_llm=lambda: resolve(deps.get_chat_completion_port)(settings),
        timezone=settings.app_timezone,
        structure_llm_enabled=settings.structure_llm_enabled,
        structure_llm_min_words=settings.structure_llm_min_words,
        structure_llm_daily_limit=settings.structure_llm_daily_limit,
        embedding_cache_enabled=settings.embedding_cache_enabled,
        proposal=ProposalOptions(
            mode=settings.task_proposal_mode,
            batch_words=settings.task_proposal_batch_words,
            call_timeout_seconds=settings.task_proposal_call_timeout_seconds,
        ),
    )

    async def purge_old_conversations() -> None:
        async with app.state.session_factory() as session:
            await conversations.purge_expired(session, settings.chat_retention_days)

    periodic: list[tuple[float, Callable[[], Awaitable[None]]]] = [(6 * 3600.0, purge_old_conversations)]
    app.state.keep_warm = None
    if settings.embedding_keep_warm_enabled and isinstance(embedding, ModalEmbeddingAdapter):
        keep_warm = KeepWarm(embedding, window_seconds=settings.embedding_keep_warm_window_seconds)
        app.state.keep_warm = keep_warm
        periodic.append((settings.embedding_keep_warm_interval_seconds, keep_warm.tick))

    return JobWorker(
        ctx=ctx,
        handlers=HANDLERS,
        periodic=periodic,
        max_concurrent=settings.job_max_concurrent,
        poll_seconds=settings.job_poll_seconds,
        stale_seconds=settings.job_stale_seconds,
    )


def create_app() -> FastAPI:
    settings = get_settings()
    production = settings.app_env == "production"
    app = FastAPI(
        title="VSF Onboarding Assistant",
        lifespan=lifespan,
        # Tài liệu API nằm dưới /api/ để cùng được proxy; tắt ở production.
        docs_url=None if production else "/api/docs",
        redoc_url=None,
        openapi_url=None if production else "/api/openapi.json",
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        supplied = request.headers.get("x-request-id", "")
        request_id = supplied if _REQUEST_ID_PATTERN.fullmatch(supplied) else uuid.uuid4().hex
        set_request_id(request_id)  # để mỗi bản ghi llm_calls nối được với request và log
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # Bộ đếm đăng nhập sai nằm trong tiến trình (MVP một worker), xem services/auth/login_throttle.py.
    app.state.login_throttle = LoginThrottle(settings.login_max_failures, settings.login_window_seconds)

    # Giới hạn số câu hỏi /chat/ask theo user_id (endpoint tốn tiền thật mỗi lần gọi), xem chat_throttle.py.
    app.state.chat_throttle = ChatThrottle(settings.chat_max_questions, settings.chat_window_seconds)

    # Theo dõi từng bước gọi LLM/embedding (2-D mở rộng); no-op nếu chưa bật/chưa cấu hình khóa.
    app.state.langfuse_tracer = LangfuseTracer(
        enabled=settings.langfuse_enabled,
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key.get_secret_value() if settings.langfuse_secret_key else None,
        host=settings.langfuse_host,
        capture_content=settings.langfuse_capture_content,
        content_max_chars=settings.langfuse_content_max_chars,
    )
    if app.state.langfuse_tracer.active:
        set_current_tracer(app.state.langfuse_tracer)
        set_observer(app.state.langfuse_tracer.start_call)

    @app.exception_handler(AuthError)
    async def auth_error_handler(_: Request, exc: AuthError) -> JSONResponse:
        # Một hình dạng lỗi duy nhất: {code, message_key, detail} (system design mục 9).
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message_key": exc.message_key, "detail": None},
            headers=exc.headers,
        )

    @app.exception_handler(PortalError)
    async def portal_error_handler(_: Request, exc: PortalError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message_key": exc.message_key, "detail": None},
            headers=exc.headers,
        )

    @app.exception_handler(ChatCompletionError)
    @app.exception_handler(EmbeddingServiceError)
    async def ai_service_error_handler(_: Request, exc: Exception) -> JSONResponse:
        # Lỗi mạng/khóa/định dạng từ LLM hoặc embedding: người dùng thấy "chưa trả lời được" thay vì lỗi 500.
        # Chỉ ghi loại lỗi, không ghi nội dung câu hỏi hay tài liệu (INV8).
        logger.warning("ai_service_unavailable type=%s", type(exc).__name__)
        return JSONResponse(
            status_code=503,
            content={"code": "ASSISTANT_UNAVAILABLE", "message_key": "chat.assistant_unavailable", "detail": None},
            headers={"Retry-After": "5"},
        )

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(chat_router)
    app.include_router(portal_document_router)
    app.include_router(portal_editor_router)
    app.include_router(portal_router)
    app.include_router(portal_version_router)
    app.include_router(ticket_router)
    app.include_router(analytics_router)
    app.include_router(viga_router)
    app.include_router(admin_router)

    if not production:
        # Trang test tay nội bộ cho Portal API (plan-portal/P4B) — cùng origin nên cookie đăng nhập
        # dùng chung, không cần CORS. Không bật ở production (giống docs_url).
        _portal_test_html = (Path(__file__).parent / "static" / "portal_test.html").read_text(encoding="utf-8")

        @app.get("/portal-test", response_class=HTMLResponse, include_in_schema=False)
        async def portal_test_page() -> str:
            return _portal_test_html

    return app


app = create_app()
