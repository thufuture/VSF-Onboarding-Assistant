"""So sánh phiên bản: ghép mục, nhận ra mục thêm, xóa, sửa, đổi tên, và diff từng từ."""

from src.services.portal.document_diff import diff_markdown, word_diff


def doc(*sections: tuple[str, str]) -> str:
    return "# Quy chế\n\n" + "\n\n".join(f"## {heading}\n\n{body}" for heading, body in sections)


BODY = {
    "Điều 1": "Nhân viên làm việc tám giờ mỗi ngày từ thứ hai đến thứ sáu. " * 6,
    "Điều 2": "Nghỉ phép năm là mười hai ngày và được cộng dồn theo thâm niên công tác. " * 6,
    "Điều 3": "Đi muộn quá ba lần trong tháng sẽ bị nhắc nhở bằng văn bản chính thức. " * 6,
}
BASE = doc(*BODY.items())


def statuses(markdown_old: str, markdown_new: str) -> list[tuple[str, str | None]]:
    return [(c.status, c.heading) for c in diff_markdown(markdown_old, markdown_new).sections]


def test_identical_documents_have_no_changes() -> None:
    result = diff_markdown(BASE, BASE)
    assert (result.added, result.removed, result.modified) == (0, 0, 0)
    assert result.unchanged == len(result.sections) > 1
    assert result.recompute.chunks_to_embed == 0 and result.recompute.estimated_seconds == 0


def test_editing_one_word_marks_only_that_section_modified() -> None:
    edited = dict(BODY, **{"Điều 2": BODY["Điều 2"].replace("mười hai", "mười lăm")})
    result = diff_markdown(BASE, doc(*edited.items()))
    assert (result.added, result.removed, result.modified) == (0, 0, 1)
    changed = next(c for c in result.sections if c.status == "modified")
    assert changed.heading == "Điều 2"
    inserted = [s.text for s in changed.segments if s.op == "insert"]
    deleted = [s.text for s in changed.segments if s.op == "delete"]
    assert any("lăm" in text for text in inserted) and any("hai" in text for text in deleted)
    assert changed.added_words >= 1 and changed.removed_words >= 1
    assert 1 <= result.recompute.chunks_to_embed < result.recompute.chunks_total
    # Ghép lại các đoạn "equal" và "insert" phải ra đúng văn bản mới, "equal" và "delete" ra đúng văn bản cũ.
    assert "".join(s.text for s in changed.segments if s.op != "delete") == edited["Điều 2"].strip()
    assert "".join(s.text for s in changed.segments if s.op != "insert") == BODY["Điều 2"].strip()


def test_added_and_removed_sections() -> None:
    added = doc(*BODY.items(), ("Điều 4", "Quy định mới hoàn toàn về làm việc từ xa vào hai ngày mỗi tuần. " * 6))
    assert statuses(BASE, added)[-1] == ("added", "Điều 4")
    removed = doc(*[(h, b) for h, b in BODY.items() if h != "Điều 2"])
    result = diff_markdown(BASE, removed)
    assert (result.added, result.removed, result.modified) == (0, 1, 0)
    assert any(c.status == "removed" and c.heading == "Điều 2" for c in result.sections)


def test_moved_section_is_not_reported_as_content_change() -> None:
    swapped = doc(("Điều 2", BODY["Điều 2"]), ("Điều 1", BODY["Điều 1"]), ("Điều 3", BODY["Điều 3"]))
    result = diff_markdown(BASE, swapped)
    assert result.modified == 0
    assert result.unchanged >= 2


def test_renamed_heading_with_same_content_is_one_modified_section() -> None:
    renamed = doc(("Điều 1", BODY["Điều 1"]), ("Điều 2 (sửa đổi)", BODY["Điều 2"]), ("Điều 3", BODY["Điều 3"]))
    result = diff_markdown(BASE, renamed)
    assert (result.added, result.removed, result.modified) == (0, 0, 1)
    change = next(c for c in result.sections if c.status == "modified")
    assert change.heading == "Điều 2 (sửa đổi)" and change.old_heading == "Điều 2"


def test_word_diff_keeps_whitespace_and_merges_runs() -> None:
    segments = word_diff("a b c d", "a x y d")
    assert "".join(s.text for s in segments if s.op != "delete") == "a x y d"
    assert "".join(s.text for s in segments if s.op != "insert") == "a b c d"
    assert [s.op for s in segments] == ["equal", "delete", "insert", "equal"]
