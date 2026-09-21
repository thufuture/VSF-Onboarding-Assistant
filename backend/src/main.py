"""Điểm vào ứng dụng: lifespan (engine DB), middleware X-Request-ID, đăng ký router."""

import re
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from src.api.routers.auth_router import router as auth_router
from src.api.routers.health_router import router as health_router
from src.config import get_settings
from src.infrastructure.persistence.engine import create_engine, create_session_factory
from src.services.auth.errors import AuthError
from src.services.auth.login_throttle import LoginThrottle
from src.services.auth.seed import assert_no_dev_accounts

# Chỉ nhận ID từ client nếu đơn giản và ngắn; nếu không thì tự tạo (tránh chèn ký tự lạ vào log/header).
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    try:
        if settings.app_env == "production":
            # Mật khẩu dev nằm trong repo: production không được chạy khi còn tài khoản dev.
            async with app.state.session_factory() as session:
                await assert_no_dev_accounts(session)
        yield
    finally:
        await engine.dispose()


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
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # Bộ đếm đăng nhập sai nằm trong tiến trình (MVP một worker), xem services/auth/login_throttle.py.
    app.state.login_throttle = LoginThrottle(settings.login_max_failures, settings.login_window_seconds)

    @app.exception_handler(AuthError)
    async def auth_error_handler(_: Request, exc: AuthError) -> JSONResponse:
        # Một hình dạng lỗi duy nhất: {code, message_key, detail} (system design mục 9).
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message_key": exc.message_key, "detail": None},
            headers=exc.headers,
        )

    app.include_router(health_router)
    app.include_router(auth_router)
    return app


app = create_app()
