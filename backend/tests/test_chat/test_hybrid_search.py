"""Đơn vị cho reciprocal_rank_fusion (mục 8, kế hoạch 2-C/2-D mở rộng) — thứ hạng, hòa điểm."""

from src.services.retrieval.hybrid_search import reciprocal_rank_fusion


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


def test_sanitize_lexical_query_removes_query_syntax_characters() -> None:
    from src.services.retrieval.hybrid_search import sanitize_lexical_query

    assert sanitize_lexical_query("[ trong tài liệu ngày 1 ] , [ bổ sung ]") == "trong tài liệu ngày 1 bổ sung"
    assert sanitize_lexical_query('a "b" (c) d:e f* g? -h +i') == "a b c d e f g h i"


def test_sanitize_lexical_query_keeps_plain_vietnamese() -> None:
    from src.services.retrieval.hybrid_search import sanitize_lexical_query

    assert sanitize_lexical_query("nghỉ phép năm bao nhiêu ngày") == "nghỉ phép năm bao nhiêu ngày"
    assert sanitize_lexical_query("[]()") == ""


def test_rrf_weights_scale_each_list() -> None:
    scores = reciprocal_rank_fusion([1], [2], k=10, weights=(0.1, 1.0))

    assert scores[1] == 0.1 / 11
    assert scores[2] == 1.0 / 11
    assert scores[2] > scores[1]


def test_rrf_default_weights_match_previous_behaviour() -> None:
    assert reciprocal_rank_fusion([1, 2], [2, 1]) == reciprocal_rank_fusion([1, 2], [2, 1], weights=(1.0, 1.0))


def test_rrf_weights_length_must_match_lists() -> None:
    import pytest

    with pytest.raises(ValueError):
        reciprocal_rank_fusion([1], [2], weights=(1.0,))


def test_bm25_reserve_adds_top_bm25_section_when_missing_from_cut() -> None:
    from src.services.retrieval.hybrid_search import select_with_bm25_reserve

    fused = [1, 2, 3, 4, 5, 6, 7]
    bm25 = [9, 7, 1]  # 9 không có trong fused: bị bỏ qua; 7 là mục BM25 đầu tiên nằm trong danh sách ứng viên

    assert select_with_bm25_reserve(fused, bm25, max_sections=4, bm25_reserve=1) == [1, 2, 3, 7]


def test_bm25_reserve_does_nothing_when_bm25_top_already_kept() -> None:
    from src.services.retrieval.hybrid_search import select_with_bm25_reserve

    fused = [1, 2, 3, 4, 5, 6]

    assert select_with_bm25_reserve(fused, [2, 1], max_sections=4, bm25_reserve=1) == [1, 2, 3, 4]


def test_bm25_reserve_disabled_matches_plain_cut() -> None:
    from src.services.retrieval.hybrid_search import select_with_bm25_reserve

    fused = [5, 4, 3, 2, 1]

    assert select_with_bm25_reserve(fused, [1], max_sections=3, bm25_reserve=0) == [5, 4, 3]
    assert select_with_bm25_reserve(fused, [1], max_sections=0, bm25_reserve=1) == fused


def test_bm25_reserve_never_takes_all_slots() -> None:
    from src.services.retrieval.hybrid_search import select_with_bm25_reserve

    result = select_with_bm25_reserve([1, 2, 3, 4], [9, 4, 3], max_sections=2, bm25_reserve=5)

    assert len(result) == 2 and result[0] == 1
