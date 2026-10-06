"""Tiến độ tạo task theo bước thật: phần trăm theo trọng số, chia lại khi bỏ bước, gom nhiều tài liệu thành một thanh."""

from typing import Any

import pytest

from src.services.portal.proposal_progress import SAVE_START, ProposalTracker


class _FakeJobProgress:
    def __init__(self) -> None:
        self.updates: list[tuple[float, str, dict[str, Any] | None]] = []

    async def update(self, percent: float, stage: str, steps: dict[str, Any] | None = None) -> None:
        self.updates.append((percent, stage, steps))


def _tracker(count: int = 1) -> tuple[ProposalTracker, _FakeJobProgress]:
    fake = _FakeJobProgress()
    return ProposalTracker(fake, [(i + 1, f"Tài liệu {i + 1}") for i in range(count)]), fake  # type: ignore[arg-type]


def _step(snapshot: dict[str, Any], key: str) -> dict[str, Any]:
    return next(step for step in snapshot["steps"] if step["key"] == key)


async def test_percent_follows_real_steps_by_weight() -> None:
    tracker, fake = _tracker()
    doc = tracker.documents[0]

    await doc.update("read", done=1, total=1)
    after_read = fake.updates[-1][0]
    await doc.update("draft", done=1, total=1)
    after_draft = fake.updates[-1][0]
    await doc.update("verify", done=1, total=1)
    await doc.update("cover", done=1, total=1)
    await doc.update("order", done=1, total=1)
    after_all = fake.updates[-1][0]

    # Trọng số 5/65/5/10/10 trên phần dành cho các bước theo tài liệu (95%).
    assert after_read == pytest.approx(SAVE_START * 5 / 95, abs=0.5)
    assert after_draft == pytest.approx(SAVE_START * 70 / 95, abs=0.5)
    assert after_all == pytest.approx(SAVE_START)


async def test_skipped_steps_hand_their_share_to_the_remaining_steps() -> None:
    tracker, fake = _tracker()
    doc = tracker.documents[0]

    await doc.update("read", done=1, total=1)
    await doc.update("draft", done=1, total=1)
    await doc.update("verify", done=1, total=1)
    await doc.skip("cover")
    await doc.skip("order")

    # Còn lại read+draft+verify = 75 trọng số, đã xong cả ba => thanh tới đúng phần cuối của bước theo tài liệu.
    assert fake.updates[-1][0] == pytest.approx(SAVE_START)
    snapshot = fake.updates[-1][2]
    assert snapshot is not None
    assert _step(snapshot, "cover")["status"] == "skipped" and _step(snapshot, "order")["status"] == "skipped"


async def test_running_step_eases_but_never_reaches_its_full_share_before_it_is_done() -> None:
    tracker, _ = _tracker()
    doc = tracker.documents[0]
    await doc.update("read", done=1, total=1)
    await doc.update("draft", done=0, total=1)

    state = doc.steps["draft"]
    assert state.started is not None
    far_future = state.started + 10_000  # chờ rất lâu mà bước vẫn chưa báo xong
    fraction = doc.fraction(far_future)

    assert fraction < 70 / 95 + 1e-9  # chưa tới phần của "draft" đầy đủ
    assert fraction > 5 / 95  # nhưng đã tiến quá phần "read"


async def test_aggregate_steps_and_percent_across_documents() -> None:
    tracker, fake = _tracker(2)
    first, second = tracker.documents

    await first.update("read", done=1, total=1)
    await second.update("read", done=1, total=1)
    await first.update("draft", done=1, total=1)
    await second.update("draft", done=0, total=1)

    percent, stage, detail = tracker.snapshot()
    draft = _step(detail, "draft")
    assert draft["status"] == "running" and draft["done"] == 1 and draft["total"] == 2
    assert _step(detail, "read")["status"] == "done"
    assert [d["version_id"] for d in detail["documents"]] == [1, 2]
    assert detail["documents"][0]["percent"] > detail["documents"][1]["percent"]
    assert "2 tài liệu" in stage and "AI đang soạn task" in stage
    assert 0 < percent < SAVE_START


async def test_failed_document_counts_as_finished_so_the_bar_does_not_stall() -> None:
    tracker, _ = _tracker(2)
    first, second = tracker.documents
    first.failed = True
    first.finish_all()
    await second.update("read", done=1, total=1)
    await second.update("draft", done=1, total=1)
    await second.update("verify", done=1, total=1)
    await second.skip("cover")
    await second.skip("order")

    percent, _, detail = tracker.snapshot()

    assert percent == pytest.approx(SAVE_START)
    assert detail["documents"][0]["failed"] is True


async def test_saving_step_pushes_to_99_and_is_the_last_step() -> None:
    tracker, fake = _tracker()
    doc = tracker.documents[0]
    for key in ("read", "draft", "verify", "cover", "order"):
        await doc.update(key, done=1, total=1)

    await tracker.saving()
    assert fake.updates[-1][2] is not None
    assert _step(fake.updates[-1][2], "save")["status"] == "running"
    assert fake.updates[-1][0] >= SAVE_START

    await tracker.saved()
    assert fake.updates[-1][0] == 99
    assert _step(fake.updates[-1][2] or {}, "save")["status"] == "done"
    assert [s["key"] for s in (fake.updates[-1][2] or {})["steps"]] == [
        "read",
        "draft",
        "verify",
        "cover",
        "order",
        "save",
    ]


async def test_progress_payload_has_no_document_content_fields() -> None:
    tracker, _ = _tracker()
    await tracker.documents[0].update("draft", done=0, total=1)

    _, _, detail = tracker.snapshot()

    assert (
        isinstance(detail["elapsed_seconds"], int) and detail["elapsed_seconds"] >= 0
    )  # đo bằng đồng hồ đơn điệu của worker
    allowed_step_keys = {"key", "status", "done", "total", "seconds"}
    assert all(set(step) <= allowed_step_keys for step in detail["steps"])
    assert all(set(doc) <= {"version_id", "title", "percent", "failed"} for doc in detail["documents"])
