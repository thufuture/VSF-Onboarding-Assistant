"""Hai bước nhẹ của Viga (chọn công cụ, viết lại câu hỏi) phải tắt suy luận ẩn của LLM; bước soạn câu trả lời thì giữ nguyên.

Căn cứ: benchmark 06/10/2026 (docs/value/benchmark-modal-llm-viga): tắt ở route + rewrite nhanh hơn khoảng 22% mà độ chính xác
không tệ đi; tắt thêm ở bước trả lời làm câu nhiều ý trả lời thiếu ý.
"""

import json
from typing import Any

import pytest

from src.services.retrieval.hybrid_search import SectionEvidence
from src.services.viga.answer_service import QuestionEvidence, answer_with_claims
from src.services.viga.query_rewrite import rewrite_query
from src.services.viga.router import route_question


class _RecordingLlm:
    def __init__(self, reply: dict[str, Any]) -> None:
        self.reply = reply
        self.reasoning_flags: list[bool] = []

    async def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        timeout_seconds: float | None = None,
        reasoning: bool = True,
        stream: bool = False,
        temperature: float | None = None,
    ) -> str:
        self.reasoning_flags.append(reasoning)
        return json.dumps(self.reply)


@pytest.mark.asyncio
async def test_route_tat_suy_luan() -> None:
    llm = _RecordingLlm({"tool": "none", "args": {}, "confidence": 0.9, "clarify": None})
    await route_question("tôi làm được bao nhiêu việc rồi", llm, None)
    assert llm.reasoning_flags == [False]


@pytest.mark.asyncio
async def test_rewrite_tat_suy_luan() -> None:
    llm = _RecordingLlm({"standalone_questions": ["Hồ sơ ngày đầu gồm những gì?"]})
    assert await rewrite_query("hồ sơ ngày đầu?", llm) == ["Hồ sơ ngày đầu gồm những gì?"]
    assert llm.reasoning_flags == [False]


@pytest.mark.asyncio
async def test_tra_loi_giu_suy_luan() -> None:
    section = SectionEvidence(
        section_id=1,
        heading="Hồ sơ",
        content="Nộp CV.",
        token_count=5,
        chunk_ids=(10,),
        score=1.0,
        document_title="Hướng dẫn",
        version_label="1.0",
        document_url="x",
        version_id=1,
    )
    llm = _RecordingLlm({"claims": []})
    await answer_with_claims([QuestionEvidence("Hồ sơ gồm gì?", [section])], llm)
    assert llm.reasoning_flags == [True]
