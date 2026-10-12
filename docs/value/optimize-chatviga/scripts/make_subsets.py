"""Tách golden 120 câu thành tập "kiểm" 50 câu và tập "chỉnh" 70 câu, theo tầng, hạt giống cố định.

Tập chỉnh chỉ dùng để chọn tham số (RRF, rerank). Tập kiểm dùng để so sánh cuối, chưa từng dùng để chọn tham số.
Trong mỗi nhóm câu hỏi, chọn xen kẽ theo độ khó rồi theo kiểu diễn đạt để cả hai tập bao quát cùng các tình huống.

Chạy từ gốc repo: python docs/value/optimize-chatviga/scripts/make_subsets.py
"""

import collections
import json
import random
from pathlib import Path

DIR = Path(__file__).resolve().parents[1]
GOLDEN = DIR / "bo-cau-hoi" / "golden_v0_nhap.jsonl"
SEED = 20261011

# số câu của tập kiểm 50 theo từng nhóm (phần còn lại của nhóm vào tập chỉnh)
QUOTA = {
    "tài liệu: một sự kiện": 14,
    "tài liệu: câu kép 2 ý": 7,
    "tài liệu: câu kép 3 ý": 5,
    "tài liệu: không có căn cứ": 4,
    "hành trình: công cụ": 6,
    "hành trình: câu kép nhiều công cụ": 4,
    "thông tin cá nhân": 3,
    "ngoài phạm vi": 3,
    "chèn lệnh": 2,
    "xã giao": 2,
}


def main() -> None:
    items = [json.loads(line) for line in GOLDEN.read_text(encoding="utf-8").splitlines()]
    rng = random.Random(SEED)
    by_group: dict[str, list[dict]] = collections.defaultdict(list)
    for item in items:
        by_group[item["category"]].append(item)

    check: list[str] = []
    for group, rows in by_group.items():
        quota = QUOTA.get(group)
        if quota is None:
            raise SystemExit(f"nhóm chưa có hạn mức: {group}")
        rng.shuffle(rows)
        # xen kẽ theo (độ khó, kiểu diễn đạt) để tập kiểm trải đều
        buckets: dict[tuple[str, str], list[dict]] = collections.defaultdict(list)
        for row in rows:
            buckets[(row.get("difficulty", ""), row.get("style", ""))].append(row)
        order: list[dict] = []
        while any(buckets.values()):
            for key in sorted(buckets):
                if buckets[key]:
                    order.append(buckets[key].pop())
        check += [row["id"] for row in order[:quota]]

    check_set = set(check)
    tune = [item["id"] for item in items if item["id"] not in check_set]
    check_ids = [item["id"] for item in items if item["id"] in check_set]

    def describe(ids: list[str]) -> dict:
        wanted = set(ids)
        chosen = [i for i in items if i["id"] in wanted]
        return {
            "số_câu": len(ids),
            "theo_nhóm": dict(collections.Counter(i["category"] for i in chosen)),
            "theo_độ_khó": dict(collections.Counter(i.get("difficulty", "") for i in chosen)),
            "theo_kiểu": dict(collections.Counter(i.get("style", "") for i in chosen)),
        }

    out = {"hạt_giống": SEED, "ghi_chú": "tập chỉnh chỉ để chọn tham số; tập kiểm dùng để so sánh cuối"}
    (DIR / "bo-cau-hoi" / "tap_kiem_50.json").write_text(
        json.dumps({**out, "id": check_ids, "mô_tả": describe(check_ids)}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (DIR / "bo-cau-hoi" / "tap_chinh_70.json").write_text(
        json.dumps({**out, "id": tune, "mô_tả": describe(tune)}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("kiểm", len(check_ids), "chỉnh", len(tune))
    print(json.dumps(describe(check_ids)["theo_nhóm"], ensure_ascii=False))


if __name__ == "__main__":
    main()
