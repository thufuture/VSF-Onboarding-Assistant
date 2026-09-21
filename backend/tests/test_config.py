import pytest
from pydantic import ValidationError

from src.config import Settings

_ENV_NAMES = ("APP_ENV", "APP_TIMEZONE", "LOG_LEVEL", "DATABASE_URL", "SESSION_SECRET", "SESSION_TTL_SECONDS")


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


def test_defaults() -> None:
    settings = Settings(_env_file=None)
    assert settings.app_env == "development"
    assert settings.app_timezone == "Asia/Ho_Chi_Minh"
    assert settings.database_url.startswith("postgresql+asyncpg://")


def test_environment_overrides_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db:5432/x")
    settings = Settings(_env_file=None)
    assert settings.app_env == "test"
    assert settings.database_url == "postgresql+asyncpg://u:p@db:5432/x"


def test_unknown_timezone_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_TIMEZONE", "Not/AZone")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_unknown_environment_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "staging")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_development_generates_a_random_session_secret_when_missing() -> None:
    first = Settings(_env_file=None)
    second = Settings(_env_file=None)
    assert first.session_secret is not None and second.session_secret is not None
    assert len(first.session_secret.get_secret_value()) >= 32
    assert first.session_secret.get_secret_value() != second.session_secret.get_secret_value()


def test_production_requires_a_session_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


@pytest.mark.parametrize(
    "weak",
    ["short", "a" * 40, "please-change-me-please-change-me-please", "my-dev-session-key-0123456789abcdef0123"],
)
def test_production_rejects_weak_session_secrets(monkeypatch: pytest.MonkeyPatch, weak: str) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SESSION_SECRET", weak)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_production_accepts_a_strong_session_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SESSION_SECRET", "f3b1c9d2a7e84f6b95a0c3d1e7b28a4f6d0c9e5b1a3f7d2c")
    settings = Settings(_env_file=None)
    assert settings.session_secret is not None
    assert settings.session_ttl_seconds == 1800
