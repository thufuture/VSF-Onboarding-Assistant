"""Embedding giả, tất định (cùng văn bản luôn ra cùng vector) — dùng cho test và CI (D6/D8, phase-2.md).
Không gọi mạng, không mang ý nghĩa ngữ nghĩa thật; chỉ để kiểm tra pipeline ghi/đọc, không đo chất lượng.
"""

from __future__ import annotations

import hashlib
import struct

_DIMENSION = 1024


class FakeEmbeddingAdapter:
    model_version = "fake-embedding-v1"
    dimension = _DIMENSION

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [_vector_for(text) for text in texts]


def _vector_for(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    needed = _DIMENSION * 4
    stream = (digest * (needed // len(digest) + 1))[:needed]
    values = struct.unpack(f"{_DIMENSION}i", stream)
    return [v / 2_147_483_648 for v in values]
