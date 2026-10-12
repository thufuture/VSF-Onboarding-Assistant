"""Hồ sơ truy hồi: legacy giữ hành vi cũ, optimized dùng cấu hình benchmark, biến môi trường từng tham số ghi đè hồ sơ."""

import pytest

from src.config import RetrievalTuning, Settings, resolve_retrieval_tuning

_TUNING_ENV = ("RETRIEVAL_PROFILE", "RRF_K", "RRF_WEIGHT_BM25", "RRF_WEIGHT_VECTOR", "RETRIEVAL_MAX_SECTIONS")


@pytest.fixture(autouse=True)
def _clean_tuning_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Một số thư viện nạp tệp .env của máy dev vào os.environ khi được import (xảy ra khi chạy sau test ingest);
    # test cấu hình phải độc lập với điều đó.
    for name in _TUNING_ENV:
        monkeypatch.delenv(name, raising=False)


def _settings(**overrides: object) -> Settings:
    # _env_file=None: test không phụ thuộc vào .env cục bộ (dev có thể đã bật hồ sơ optimized).
    return Settings(_env_file=None, session_secret="x" * 40, **overrides)  # type: ignore[arg-type]


def test_legacy_profile_is_default_and_keeps_old_behaviour() -> None:
    assert resolve_retrieval_tuning(_settings()) == RetrievalTuning(
        rrf_k=60, weight_bm25=1.0, weight_vector=1.0, max_sections=0
    )


def test_optimized_profile_uses_benchmark_values() -> None:
    tuning = resolve_retrieval_tuning(_settings(retrieval_profile="optimized"))

    assert tuning == RetrievalTuning(rrf_k=10, weight_bm25=0.1, weight_vector=1.0, max_sections=5)


def test_explicit_values_override_profile() -> None:
    tuning = resolve_retrieval_tuning(_settings(retrieval_profile="optimized", rrf_k=30, retrieval_max_sections=0))

    assert tuning.rrf_k == 30
    assert tuning.max_sections == 0
    assert tuning.weight_bm25 == 0.1
