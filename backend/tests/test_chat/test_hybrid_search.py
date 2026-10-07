"""Đơn vị cho reciprocal_rank_fusion (mục 8, kế hoạch 2-C/2-D mở rộng) — thứ hạng, hòa điểm."""

from src.services.retrieval.hybrid_search import bm25_safe_query, reciprocal_rank_fusion


def test_item_ranked_first_in_both_lists_scores_highest() -> None:
    scores = reciprocal_rank_fusion([1, 2, 3], [1, 3, 2])

    assert max(scores, key=lambda item_id: scores[item_id]) == 1


def test_item_only_in_one_list_still_gets_a_score() -> None:
    scores = reciprocal_rank_fusion([1, 2], [3])

    assert set(scores) == {1, 2, 3}
    assert scores[3] > 0


def test_tie_when_ranked_equally_in_both_lists() -> None:
    scores = reciprocal_rank_fusion([1, 2], [2, 1])

    assert scores[1] == scores[2]


def test_higher_rank_gives_higher_score() -> None:
    scores = reciprocal_rank_fusion([1, 2, 3])

    assert scores[1] > scores[2] > scores[3]


def test_empty_lists_give_empty_scores() -> None:
    assert reciprocal_rank_fusion([], []) == {}


def test_bm25_query_drops_the_search_engine_syntax_characters() -> None:
    # Dấu hai chấm của một câu hỏi bình thường từng làm ParadeDB báo "could not parse query string" và Viga trả ERROR.
    assert bm25_safe_query("kiểm tra langfuse : nhận laptop ở đâu ?") == "kiểm tra langfuse nhận laptop ở đâu"
    raw = r'nghỉ phép: (12 ngày) "mỗi năm" +a -b ^2 ~1 *x? [y] {z} ! \ /'
    assert bm25_safe_query(raw) == "nghỉ phép 12 ngày mỗi năm a b 2 1 x y z"


def test_bm25_query_keeps_vietnamese_letters_digits_and_compound_underscores() -> None:
    assert bm25_safe_query("đăng_ký faceid ở tầng 14") == "đăng_ký faceid ở tầng 14"


def test_bm25_query_neutralises_operator_words() -> None:
    assert bm25_safe_query("Nghỉ AND phép OR NOT thử") == "nghỉ and phép or not thử"


def test_bm25_query_with_only_punctuation_is_empty() -> None:
    assert bm25_safe_query(" : ( ) ? ") == ""
