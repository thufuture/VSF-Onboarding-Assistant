"""Lưu file tài liệu gốc (2-B). Hai adapter chọn bằng `settings.storage_provider`:

- `local`: ghi vào `STORAGE_PATH/documents/<file_checksum><đuôi file>` trên đĩa — mặc định, an toàn cho
  dev/CI (không cần tài khoản ngoài).
- `cloudinary`: đẩy bytes lên Cloudinary (giống Ralion `src/services/storage_service.py`), DB chỉ lưu
  `secure_url` làm `storage_key`, không lưu file. Dùng thư mục riêng `vsf-documents/` để tách khỏi dữ liệu
  Ralion khi dùng chung tài khoản.

Cả hai đều idempotent theo `file_checksum` (sha256 của file gốc, không phải của Markdown): cùng file ghi lại không tạo file trùng (local: cùng tên
nên tự ghi đè cùng nội dung; Cloudinary: `overwrite=True` với `public_id` theo checksum).
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class StoragePort(Protocol):
    async def store(self, content: bytes, *, checksum: str, filename: str) -> str:
        """Lưu file, trả về `storage_key` (đường dẫn tương đối hoặc URL) để ghi vào `document_versions`."""
        ...


class LocalStorageAdapter:
    def __init__(self, storage_path: str) -> None:
        self._root = Path(storage_path)

    async def store(self, content: bytes, *, checksum: str, filename: str) -> str:
        documents_dir = self._root / "documents"
        documents_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(filename).suffix
        target = documents_dir / f"{checksum}{suffix}"
        target.write_bytes(content)
        return str(Path("documents") / target.name)


class CloudinaryStorageAdapter:
    def __init__(self, *, cloud_name: str, api_key: str, api_secret: str) -> None:
        if not cloud_name or not api_key or not api_secret:
            raise ValueError("cần CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET")
        self._cloud_name = cloud_name
        self._api_key = api_key
        self._api_secret = api_secret

    async def store(self, content: bytes, *, checksum: str, filename: str) -> str:
        import asyncio

        import cloudinary
        import cloudinary.uploader

        # public_id PHẢI có đuôi file — thiếu đuôi thì Cloudinary trả Content-Type: application/octet-stream
        # và Content-Disposition không có phần mở rộng, trình duyệt/OS không biết mở bằng ứng dụng nào
        # (bug thật đã phát hiện: link mở ra tải file tên toàn hash, không có .docx).
        suffix = Path(filename).suffix
        public_id = f"{checksum}{suffix}"

        def upload() -> str:
            cloudinary.config(cloud_name=self._cloud_name, api_key=self._api_key, api_secret=self._api_secret)
            result = cloudinary.uploader.upload(
                content,
                resource_type="raw",
                folder="vsf-documents",
                public_id=public_id,
                overwrite=True,
            )
            return str(result["secure_url"])

        # cloudinary.uploader.upload đồng bộ (chặn); chạy trong thread để không chặn event loop.
        return await asyncio.to_thread(upload)
