"""Chọn adapter embedding/lưu trữ theo cấu hình (`settings.embedding_provider`, `settings.storage_provider`).
Tách riêng khỏi `ingest_service.py` để service chỉ nhận `EmbeddingPort`/`StoragePort` đã dựng sẵn (dễ test
bằng adapter giả), còn CLI/nơi khởi chạy thật mới cần biết tới `Settings`.
"""

from __future__ import annotations

from src.config import Settings
from src.services.ingest.embedding.fake_adapter import FakeEmbeddingAdapter
from src.services.ingest.embedding.modal_adapter import ModalEmbeddingAdapter
from src.services.ingest.embedding.port import EmbeddingPort
from src.services.ingest.storage import CloudinaryStorageAdapter, LocalStorageAdapter, StoragePort


def build_embedding_port(settings: Settings) -> EmbeddingPort:
    if settings.embedding_provider == "fake":
        return FakeEmbeddingAdapter()
    return ModalEmbeddingAdapter(
        endpoint=settings.embedding_endpoint or "",
        api_key=settings.embedding_api_key.get_secret_value() if settings.embedding_api_key else "",
        connect_timeout=settings.ingestion_embedding_connect_timeout_seconds,
        read_timeout=settings.ingestion_embedding_read_timeout_seconds,
        max_attempts=settings.ingestion_embedding_max_attempts,
        backoff_initial=settings.ingestion_embedding_backoff_initial_seconds,
        backoff_multiplier=settings.ingestion_embedding_backoff_multiplier,
        backoff_max=settings.ingestion_embedding_backoff_max_seconds,
    )


def build_storage_port(settings: Settings) -> StoragePort:
    if settings.storage_provider == "cloudinary":
        return CloudinaryStorageAdapter(
            cloud_name=settings.cloudinary_cloud_name or "",
            api_key=settings.cloudinary_api_key or "",
            api_secret=settings.cloudinary_api_secret.get_secret_value() if settings.cloudinary_api_secret else "",
        )
    return LocalStorageAdapter(settings.storage_path)
