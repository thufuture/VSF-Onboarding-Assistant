from src.services.viga.chat_throttle import ChatThrottle


def test_allows_questions_under_the_limit() -> None:
    throttle = ChatThrottle(max_questions=3, window_seconds=60)

    for _ in range(3):
        assert throttle.retry_after(user_id=1) == 0
        throttle.record_question(user_id=1)

    assert throttle.retry_after(user_id=1) > 0


def test_blocks_after_limit_reached_in_window() -> None:
    throttle = ChatThrottle(max_questions=1, window_seconds=60)

    throttle.record_question(user_id=1)

    assert throttle.retry_after(user_id=1) > 0


def test_different_users_have_independent_counters() -> None:
    throttle = ChatThrottle(max_questions=1, window_seconds=60)

    throttle.record_question(user_id=1)

    assert throttle.retry_after(user_id=1) > 0
    assert throttle.retry_after(user_id=2) == 0
