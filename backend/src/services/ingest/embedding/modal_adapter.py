"""Adapter gọi dịch vụ embedding BGE-M3 trên Modal (quyết định D1, phase-2.md).

Hợp đồng (đối chiếu Ralion `src/infrastructure/ai/modal_embedding_adapter.py`, viết lại đơn giản hơn,
không mang theo các trừu tượng RequestBudget/RetryExecutor của Ralion — không cần cho quy mô MVP):
`POST {endpoint}/embed` với `{"texts": [...]}` (tối đa 32 chuỗi/lần), header `Authorization: Bearer <khóa>`,
trả `{"vectors": [[...]], "model_version": str, "dimension": int}`.

Xử lý lỗi theo mục 11.4 của kế hoạch 2-B: lỗi mạng/5xx/429 thì thử lại có giới hạn; 401/403 (khóa sai) thì
dừng ngay, không thử lại vô ích; số chiều hoặc số lượng vector sai thì coi là lỗi hợp đồng, không ghi DB.
"""

from __future__ import annotations

import asyncio

import httpx


class EmbeddingServiceError(Exception):
    """Lỗi khi gọi dịch vụ embedding — người gọi (ingest_service) phải dừng, không ghi DB nửa vời."""


class ModalEmbeddingAdapter:
    MAX_BATCH_SIZE = 32
    EXPECTED_DIMENSION = 1024

    def __init__(
        self,
        *,
        endpoint: str,
        api_key: str,
        connect_timeout: float,
        read_timeout: float,
        max_attempts: int,
        backoff_initial: float,
        backoff_multiplier: float,
        backoff_max: float,
    ) -> None:
        if not endpoint or not api_key:
            raise ValueError("cần EMBEDDING_ENDPOINT và EMBEDDING_API_KEY")
        self._url = f"{endpoint.rstrip('/')}/embed"
        self._api_key = api_key
        self._connect_timeout = connect_timeout
        self._read_timeout = read_timeout
        self._max_attempts = max_attempts
        self._backoff_initial = backoff_initial
        self._backoff_multiplier = backoff_multiplier
        self._backoff_max = backoff_max
        self.dimension = self.EXPECTED_DIMENSION
        # Cập nhật sau lần gọi thành công đầu tiên; endpoint là nguồn sự thật cho phiên bản model thật sự chạy.
        self.model_version = "unknown"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors: list[list[float]] = []
        async with httpx.AsyncClient() as client:
            for start in range(0, len(texts), self.MAX_BATCH_SIZE):
                batch = texts[start : start + self.MAX_BATCH_SIZE]
                vectors.extend(await self._embed_batch(client, batch))
        return vectors

    async def _embed_batch(self, client: httpx.AsyncClient, batch: list[str]) -> list[list[float]]:
        last_error: EmbeddingServiceError | None = None
        delay = self._backoff_initial
        for attempt in range(1, self._max_attempts + 1):
            try:
                response = await client.post(
                    self._url,
                    json={"texts": batch},
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    timeout=httpx.Timeout(self._read_timeout, connect=self._connect_timeout),
                )
            except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as exc:
                last_error = EmbeddingServiceError(f"lỗi mạng khi gọi embedding: {exc}")
            else:
                if response.status_code in (401, 403):
                    # Khóa sai/hết hạn không tự hết bằng thử lại (mục 11.4).
                    raise EmbeddingServiceError(
                        f"dịch vụ embedding từ chối xác thực ({response.status_code}) — kiểm tra EMBEDDING_API_KEY"
                    )
                if response.status_code >= 500 or response.status_code == 429:
                    last_error = EmbeddingServiceError(f"dịch vụ embedding lỗi tạm thời: {response.status_code}")
                elif response.status_code >= 400:
                    raise EmbeddingServiceError(f"yêu cầu embedding sai: {response.status_code} {response.text[:200]}")
                else:
                    return self._parse_response(response, len(batch))
            if attempt < self._max_attempts:
                await asyncio.sleep(min(delay, self._backoff_max))
                delay *= self._backoff_multiplier
        raise last_error or EmbeddingServiceError("gọi embedding thất bại không rõ lý do")

    def _parse_response(self, response: httpx.Response, expected_count: int) -> list[list[float]]:
        try:
            data = response.json()
        except ValueError as exc:
            raise EmbeddingServiceError("dịch vụ embedding trả JSON không hợp lệ") from exc
        dimension = data.get("dimension")
        if dimension != self.EXPECTED_DIMENSION:
            raise EmbeddingServiceError(
                f"dịch vụ embedding trả số chiều sai: {dimension}, cần {self.EXPECTED_DIMENSION}"
            )
        vectors = data.get("vectors")
        if (
            not isinstance(vectors, list)
            or len(vectors) != expected_count
            or any(not isinstance(v, list) or len(v) != self.EXPECTED_DIMENSION for v in vectors)
        ):
            raise EmbeddingServiceError("dịch vụ embedding trả số vector không khớp số văn bản gửi lên")
        self.model_version = str(data.get("model_version") or self.model_version)
        self.dimension = dimension
        return vectors
