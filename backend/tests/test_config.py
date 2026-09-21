import pytest
from pydantic import ValidationError

from src.config import Settings

_ENV_NAMES = ("APP_ENV", "APP_TIMEZONE", "LOG_LEVEL", "DATABASE_URL")


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
