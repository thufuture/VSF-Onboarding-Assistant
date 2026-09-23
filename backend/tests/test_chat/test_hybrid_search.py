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
