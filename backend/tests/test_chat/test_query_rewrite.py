"""Đơn vị cho rewrite_query (mục 5, kế hoạch 2-C/2-D mở rộng): 1 ý -> mảng 1 phần tử, nhiều ý -> mảng
nhiều phần tử, LLM trả sai định dạng -> lùi về câu gốc."""

import json

from src.infrastructure.ai.fake_chat_completion import FakeChatCompletion
from src.services.chat.query_rewrite import MAX_SUBQUESTION_LENGTH, MAX_SUBQUESTIONS, SYSTEM_PROMPT, rewrite_query


async def test_single_intent_question_returns_one_element() -> None:
    llm = FakeChatCompletion(json.dumps({"standalone_questions": ["Nghỉ phép năm được bao nhiêu ngày?"]}))

    result = await rewrite_query("nghi phep nam may ngay", llm)

    assert result == ["Nghỉ phép năm được bao nhiêu ngày?"]


async def test_multi_intent_question_splits_into_multiple_elements() -> None:
    # Ví dụ thật của bạn: "ngày mai tôi đi làm mấy giờ ở hcm, mentor tôi là ai"
    llm = FakeChatCompletion(
        json.dumps(
            {
                "standalone_questions": [
                    "Giờ làm việc tại văn phòng Hồ Chí Minh là mấy giờ?",
                    "Mentor cá nhân của nhân viên là ai?",
                ]
            }
        )
    )

    result = await rewrite_query("ngày mai tôi đi làm mấy giờ ở hcm, mentor tôi là ai", llm)

    assert len(result) == 2
    assert "Hồ Chí Minh" in result[0]
    assert "Mentor" in result[1]


async def test_malformed_json_falls_back_to_original_question() -> None:
    llm = FakeChatCompletion("không phải JSON")

    result = await rewrite_query("câu hỏi gốc", llm)

    assert result == ["câu hỏi gốc"]


async def test_missing_key_falls_back_to_original_question() -> None:
    llm = FakeChatCompletion(json.dumps({"wrong_key": []}))

    result = await rewrite_query("câu hỏi gốc", llm)

    assert result == ["câu hỏi gốc"]


async def test_empty_array_falls_back_to_original_question() -> None:
    llm = FakeChatCompletion(json.dumps({"standalone_questions": []}))

    result = await rewrite_query("câu hỏi gốc", llm)

    assert result == ["câu hỏi gốc"]


async def test_empty_original_question_with_bad_llm_response_returns_empty() -> None:
    llm = FakeChatCompletion("hỏng")

    result = await rewrite_query("   ", llm)

    assert result == []


def test_system_prompt_has_injection_defense() -> None:
    # Đây là nơi DUY NHẤT LLM thấy nguyên văn câu hỏi thô của user (mục 4.1, 2-e-prompt-guardrail-rerank/03).
    assert "DỮ LIỆU" in SYSTEM_PROMPT
    assert "<user_input>" in SYSTEM_PROMPT


async def test_user_question_is_wrapped_in_user_input_tag() -> None:
    captured: dict[str, str] = {}

    def capture(_system_prompt: str, user_prompt: str) -> str:
        captured["user_prompt"] = user_prompt
        return json.dumps({"standalone_questions": ["ok"]})

    await rewrite_query("câu hỏi gốc", FakeChatCompletion(capture))

    assert captured["user_prompt"] == "<user_input>câu hỏi gốc</user_input>"


async def test_too_many_subquestions_are_cut_to_max() -> None:
    many = [f"câu {i}" for i in range(MAX_SUBQUESTIONS + 2)]
    llm = FakeChatCompletion(json.dumps({"standalone_questions": many}))

    result = await rewrite_query("câu hỏi gốc", llm)

    assert len(result) == MAX_SUBQUESTIONS


async def test_each_subquestion_is_cut_to_max_length() -> None:
    long_question = "a" * (MAX_SUBQUESTION_LENGTH + 50)
    llm = FakeChatCompletion(json.dumps({"standalone_questions": [long_question]}))

    result = await rewrite_query("câu hỏi gốc", llm)

    assert len(result[0]) == MAX_SUBQUESTION_LENGTH


async def test_abnormally_large_result_falls_back_to_original_question() -> None:
    # Dấu hiệu LLM lỗi nặng (hoặc injection yêu cầu "trả về 100 câu hỏi") — không cắt bớt, bỏ hẳn kết quả.
    huge = [f"câu {i}" for i in range(30)]
    llm = FakeChatCompletion(json.dumps({"standalone_questions": huge}))

    result = await rewrite_query("câu hỏi gốc", llm)

    assert result == ["câu hỏi gốc"]
