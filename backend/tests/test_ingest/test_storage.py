"""`CloudinaryStorageAdapter` — public_id PHẢI giữ đuôi file gốc.

Bug thật đã phát hiện (kiểm bằng curl thật lên Cloudinary, không phải đoán): thiếu đuôi file khiến
Cloudinary trả `Content-Type: application/octet-stream` và `Content-Disposition` không có phần mở rộng —
trình duyệt/OS không biết mở file (.docx) bằng ứng dụng nào khi người dùng bấm "Mở tài liệu".
"""

from __future__ import annotations

from typing import Any

import pytest

from src.services.ingest.storage import CloudinaryStorageAdapter, LocalStorageAdapter


async def test_cloudinary_public_id_keeps_original_extension(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_upload(_content: bytes, **kwargs: Any) -> dict[str, str]:
        captured.update(kwargs)
        return {"secure_url": "https://res.cloudinary.com/demo/raw/upload/vsf-documents/abc.docx"}

    import cloudinary.uploader

    monkeypatch.setattr(cloudinary.uploader, "upload", fake_upload)
    monkeypatch.setattr("cloudinary.config", lambda **_kwargs: None)

    adapter = CloudinaryStorageAdapter(cloud_name="demo", api_key="k", api_secret="s")
    await adapter.store(b"noi dung", content_checksum="abc123", filename="Chinh_sach.docx")

    assert captured["public_id"] == "abc123.docx"


async def test_cloudinary_public_id_handles_no_extension(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_upload(_content: bytes, **kwargs: Any) -> dict[str, str]:
        captured.update(kwargs)
        return {"secure_url": "https://res.cloudinary.com/demo/raw/upload/vsf-documents/abc"}

    import cloudinary.uploader

    monkeypatch.setattr(cloudinary.uploader, "upload", fake_upload)
    monkeypatch.setattr("cloudinary.config", lambda **_kwargs: None)

    adapter = CloudinaryStorageAdapter(cloud_name="demo", api_key="k", api_secret="s")
    await adapter.store(b"noi dung", content_checksum="abc123", filename="noextension")

    assert captured["public_id"] == "abc123"


async def test_local_storage_already_kept_extension(tmp_path: Any) -> None:
    # Đối chứng: LocalStorageAdapter đã làm đúng từ đầu (dùng làm mẫu khi sửa CloudinaryStorageAdapter).
    adapter = LocalStorageAdapter(str(tmp_path))

    key = await adapter.store(b"noi dung", content_checksum="abc123", filename="Chinh_sach.docx")

    assert key.endswith("abc123.docx")
