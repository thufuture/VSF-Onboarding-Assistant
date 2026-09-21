"""Điểm vào ứng dụng: lifespan (engine DB), middleware X-Request-ID, đăng ký router."""

import re
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response

from src.api.routers.health_router import router as health_router
from src.config import get_settings
from src.infrastructure.persistence.engine import create_engine, create_session_factory

# Chỉ nhận ID từ client nếu đơn giản và ngắn; nếu không thì tự tạo (tránh chèn ký tự lạ vào log/header).
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    engine = create_engine(get_settings().database_url)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    try:
        yield
    finally:
        await engine.dispose()


def create_app() -> FastAPI:
    production = get_settings().app_env == "production"
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
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    app.include_router(health_router)
    return app


app = create_app()
