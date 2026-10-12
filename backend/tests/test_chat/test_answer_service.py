"""Đơn vị cho answer_with_claims (mục 6, kế hoạch 2-C/2-D mở rộng): claims[] cho nhiều câu hỏi, không
gọi LLM khi không có evidence, hỏng hợp đồng JSON thì ép NO_BASIS, bù claim bị LLM bỏ sót."""

import json

from src.infrastructure.ai.fake_chat_completion import FakeChatCompletion
from src.services.retrieval.hybrid_search import SectionEvidence
from src.services.viga.answer_service import QuestionEvidence, answer_with_claims

_SECTION = SectionEvidence(
    section_id=62,
    heading="5.1 Mức hưởng",
    content="Mỗi nhân viên chính thức được hưởng 12 ngày phép năm có lương.",
    token_count=12,
    chunk_ids=(10,),
    score=0.9,
    document_title="Chính sách nghỉ phép năm",
    version_label="2.0",
    document_url="https://res.cloudinary.com/demo/raw/upload/leave-policy.docx",
    version_id=1,
)


async def test_no_llm_call_when_no_evidence_for_any_question() -> None:
    calls: list[str] = []

    def track(system: str, user: str) -> str:
        calls.append(user)
        return json.dumps({"claims": []})

    llm = FakeChatCompletion(track)
    items = [QuestionEvidence("Câu hỏi không có căn cứ", sections=[])]

    claims = await answer_with_claims(items, llm)

    assert calls == []  # không gọi LLM (tiết kiệm chi phí, mục 6)
    assert len(claims) == 1
    assert claims[0].response_type == "NO_BASIS"
    assert claims[0].reason_code == "no_evidence"


async def test_answer_claim_parsed_correctly() -> None:
    llm = FakeChatCompletion(
        json.dumps(
            {
                "claims": [
                    {
                        "question": "Mức hưởng phép năm là bao nhiêu?",
                        "response_type": "ANSWER",
                        "text": "12 ngày phép năm có lương.",
                        "quote": "Mỗi nhân viên chính thức được hưởng 12 ngày phép năm có lương.",
                        "chunk_id": 10,
                    }
                ]
            }
        )
    )
    items = [QuestionEvidence("Mức hưởng phép năm là bao nhiêu?", sections=[_SECTION])]

    [claim] = await answer_with_claims(items, llm)

    assert claim.response_type == "ANSWER"
    assert claim.chunk_id == 10
    assert claim.quote is not None


async def test_multi_question_produces_multiple_claims() -> None:
    llm = FakeChatCompletion(
        json.dumps(
            {
                "claims": [
                    {
                        "question": "Câu 1",
                        "response_type": "ANSWER",
                        "text": "a",
                        "quote": "Mỗi nhân viên chính thức được hưởng 12 ngày phép năm có lương.",
                        "chunk_id": 10,
                    },
                    {
                        "question": "Câu 2",
                        "response_type": "NO_BASIS",
                        "reason_code": "out_of_scope",
                        "text": None,
                        "quote": None,
                        "chunk_id": None,
                    },
                ]
            }
        )
    )
    items = [
        QuestionEvidence("Câu 1", sections=[_SECTION]),
        QuestionEvidence("Câu 2", sections=[]),
    ]

    claims = await answer_with_claims(items, llm)

    assert len(claims) == 2
    assert claims[0].response_type == "ANSWER"
    assert claims[1].response_type == "NO_BASIS"
    assert claims[1].reason_code == "out_of_scope"


async def test_malformed_llm_response_forces_no_basis_for_all_questions() -> None:
    llm = FakeChatCompletion("không phải JSON")
    items = [QuestionEvidence("Câu 1", sections=[_SECTION]), QuestionEvidence("Câu 2", sections=[_SECTION])]

    claims = await answer_with_claims(items, llm)

    assert len(claims) == 2
    assert all(c.response_type == "NO_BASIS" and c.reason_code == "llm_contract_error" for c in claims)


async def test_llm_skips_a_question_gets_backfilled_with_no_basis() -> None:
    llm = FakeChatCompletion(
        json.dumps(
            {
                "claims": [
                    {
                        "question": "Câu 1",
                        "response_type": "ANSWER",
                        "text": "a",
                        "quote": "Mỗi nhân viên chính thức được hưởng 12 ngày phép năm có lương.",
                        "chunk_id": 10,
                    },
                ]
            }
        )
    )
    items = [QuestionEvidence("Câu 1", sections=[_SECTION]), QuestionEvidence("Câu 2", sections=[_SECTION])]

    claims = await answer_with_claims(items, llm)

    by_question = {c.question: c for c in claims}
    assert by_question["Câu 1"].response_type == "ANSWER"
    assert by_question["Câu 2"].response_type == "NO_BASIS"
    assert by_question["Câu 2"].reason_code == "llm_skipped_question"


async def test_empty_items_returns_empty_without_calling_llm() -> None:
    calls: list[str] = []

    def track(system: str, user: str) -> str:
        calls.append(user)
        return "{}"

    claims = await answer_with_claims([], FakeChatCompletion(track))

    assert claims == []
    assert calls == []


def test_use_reasoning_modes() -> None:
    from src.services.viga.answer_service import use_reasoning

    assert use_reasoning(1, "always") is True
    assert use_reasoning(3, "off") is False
    assert use_reasoning(1, "adaptive") is False
    assert use_reasoning(2, "adaptive") is True
