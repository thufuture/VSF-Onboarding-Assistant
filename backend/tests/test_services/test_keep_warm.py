"""Giữ dịch vụ embedding ấm: chỉ gọi khi gần đây có hoạt động, không xếp chồng, lỗi không lan ra."""

import asyncio

from src.services.ingest.embedding.keep_warm import KeepWarm


class FakeEmbedding:
    def __init__(self, fail: bool = False, delay: float = 0.0) -> None:
        self.calls: list[list[str]] = []
        self.fail = fail
        self.delay = delay

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.fail:
            raise RuntimeError("mạng lỗi")
        return [[0.0] for _ in texts]


async def test_tick_does_nothing_until_someone_is_active_then_pings_once_per_tick() -> None:
    embedding = FakeEmbedding()
    warm = KeepWarm(embedding, window_seconds=600)  # type: ignore[arg-type]

    await warm.tick()
    assert embedding.calls == []  # chưa ai dùng: không tốn GPU

    warm.touch()
    await warm.tick()
    await warm.tick()
    assert len(embedding.calls) == 2 and embedding.calls[0] == ["khởi động"]


async def test_stops_pinging_after_the_activity_window_ends() -> None:
    embedding = FakeEmbedding()
    warm = KeepWarm(embedding, window_seconds=0.05)  # type: ignore[arg-type]
    warm.touch()
    await warm.tick()
    await asyncio.sleep(0.08)

    assert warm.active() is False
    await warm.tick()
    assert len(embedding.calls) == 1  # hết hoạt động thì dừng, Modal tự tắt


async def test_wake_runs_in_the_background_and_does_not_stack_pings() -> None:
    embedding = FakeEmbedding(delay=0.05)
    warm = KeepWarm(embedding, window_seconds=600)  # type: ignore[arg-type]

    warm.wake()
    warm.wake()  # đang khởi động nguội: lần thứ hai không gọi chồng
    await asyncio.sleep(0.01)
    await warm.tick()
    await asyncio.sleep(0.1)

    assert len(embedding.calls) == 1


async def test_network_errors_are_swallowed() -> None:
    warm = KeepWarm(FakeEmbedding(fail=True), window_seconds=600)  # type: ignore[arg-type]
    warm.touch()

    await warm.tick()  # không ném lỗi

    assert warm.active() is True
