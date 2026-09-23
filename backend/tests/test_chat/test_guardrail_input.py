from src.services.chat.guardrail_input import INJECTION_DEFENSE_NOTE, wrap_user_input


def test_injection_defense_note_is_not_empty() -> None:
    assert INJECTION_DEFENSE_NOTE.strip()
    assert "<user_input>" in INJECTION_DEFENSE_NOTE


def test_wrap_user_input_wraps_in_tag() -> None:
    assert wrap_user_input("xin chào") == "<user_input>xin chào</user_input>"


def test_wrap_user_input_does_not_escape_content() -> None:
    # Không phải HTML render — chỉ là delimiter văn bản cho prompt, không cần escape.
    assert wrap_user_input("<b>") == "<user_input><b></user_input>"
