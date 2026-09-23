import pytest
from pydantic import ValidationError

from src.dto.request.chat_request_dto import ChatAskRequestDTO


def test_accepts_normal_question() -> None:
    dto = ChatAskRequestDTO(question="Nghỉ phép năm bao nhiêu ngày?")
    assert dto.question == "Nghỉ phép năm bao nhiêu ngày?"


def test_strips_surrounding_whitespace() -> None:
    dto = ChatAskRequestDTO(question="  câu hỏi  ")
    assert dto.question == "câu hỏi"


def test_rejects_whitespace_only_question() -> None:
    # min_length=1 vẫn cho qua chuỗi toàn khoảng trắng — chặn thêm ở field_validator.
    with pytest.raises(ValidationError):
        ChatAskRequestDTO(question="   ")


def test_rejects_empty_question() -> None:
    with pytest.raises(ValidationError):
        ChatAskRequestDTO(question="")


def test_rejects_question_over_max_length() -> None:
    with pytest.raises(ValidationError):
        ChatAskRequestDTO(question="a" * 2001)
