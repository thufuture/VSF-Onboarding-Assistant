"""Cổng (Protocol) cho dịch vụ embedding — hai adapter: `ModalEmbeddingAdapter` (thật) và
`FakeEmbeddingAdapter` (giả, tất định, dùng cho test/CI — quyết định D6/D8, phase-2.md)."""

from __future__ import annotations

from typing import Protocol


class EmbeddingPort(Protocol):
    model_version: str
    dimension: int

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Trả về danh sách vector cùng thứ tự với `texts`. Không được trả thiếu/thừa phần tử."""
        ...
