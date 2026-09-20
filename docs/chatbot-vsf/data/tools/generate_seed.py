"""Sinh bộ dữ liệu test: tài liệu PDF/DOCX, manifest, registry JSON, câu hỏi vàng, danh sách nguồn công khai, README.

Chạy:  python tools/generate_seed.py      (idempotent: dựng lại các pack sinh tự động, giữ nguyên real_public đã có)
Yêu cầu: pip install -r tools/requirements.txt ; font Arial hoặc DejaVu (đặt VSF_FONT_DIR nếu cần).
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import builders  # noqa: E402
from blocks import blocks_text  # noqa: E402
import content_documents as cd  # noqa: E402
import content_golden as cg  # noqa: E402
import content_registry as cr  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "documents"
GENERATED_PACKS = ["core", "format_edge", "conflict", "injection", "ingest_defects"]
# Thư mục chứa PDF luật công khai để chép vào documents/real_public/ (tùy chọn, không commit).
# Đặt biến môi trường VSF_LAB_DIRS (nhiều đường dẫn, ngăn cách bằng dấu ; trên Windows hoặc : trên Linux/macOS).
# Mặc định rỗng. CHỈ chạy generate_seed.py trên máy có documents/real_public/ (hoặc đặt VSF_LAB_DIRS):
# thiếu tệp thì các dòng real_public bị bỏ khỏi manifest và README.
LAB_DIRS = [Path(p) for p in os.environ.get("VSF_LAB_DIRS", "").split(os.pathsep) if p.strip()]

PACKS = {
    "core": "Kho chính, không mâu thuẫn nhau; dùng cho phần lớn câu hỏi. Gồm chính sách, quy trình onboarding và hai bản tổng hợp công khai về VSF.",
    "format_edge": "Định dạng khó: bảng gộp ô, DOCX không heading, PDF không heading.",
    "conflict": "Tài liệu cố tình mâu thuẫn với core (chỉ nạp khi test conflicting_sources).",
    "injection": "Tài liệu chứa câu lệnh kiểu prompt injection (chỉ nạp khi test an toàn).",
    "ingest_defects": "File phải bị từ chối hoặc cần OCR khi upload: scan, bí mật, chứa secret, hỏng, sai loại file.",
    "real_public": "Tài liệu thật công khai (luật lao động, v.v.). Không commit; bổ sung thêm bằng cách tải tay theo manifests/real_public_sources.csv.",
}

MANUAL_SOURCES = [
    ("M01", "VinUni Career Advancement Guidebook", "https://vinuni.edu.vn/wp-content/uploads/2020/07/Career-Advancement-Guidebook.pdf", "Tải PDF trực tiếp bằng trình duyệt", "PDF", "en"),
    ("M02", "VinUni Employees Code of Conduct (trang chính sách)", "https://policy.vinuni.edu.vn/all-policies/code-of-conduct/", "Mở bằng trình duyệt rồi In → Lưu thành PDF (công cụ tự động bị 403)", "PDF (in từ web)", "en"),
    ("M03", "VinUni Learning and Development Guidelines", "https://policy.vinuni.edu.vn/all-policies/learning-and-development-guidelines/", "In trang thành PDF", "PDF (in từ web)", "en"),
    ("M04", "Vingroup - Chính sách bảo vệ dữ liệu cá nhân", "https://vingroup.net/phat-trien-ben-vung/3211/chinh-sach-bao-ve-du-lieu-ca-nhan", "In trang thành PDF", "PDF (in từ web)", "vi"),
    ("M05", "Vingroup - Quy chế quản trị (các văn bản đính kèm)", "https://vingroup.net/quan-he-co-dong/ho-so-doanh-nghiep/quy-che-quan-tri", "Mở trang, tải từng văn bản đính kèm", "PDF", "vi"),
    ("M06", "Vinamilk - Bộ quy tắc ứng xử", "https://d8um25gjecm9v.cloudfront.net/cms/Bo_quy_tac_ung_xu_VI_fdffd72e5f.pdf", "Tải PDF trực tiếp", "PDF", "vi"),
    ("M07", "Electrolux - Bộ quy tắc ứng xử (tiếng Việt)", "https://www.electroluxgroup.com/wp-content/uploads/sites/2/2015/04/code-of-conduct-vietnamese-b.pdf", "Tải PDF trực tiếp", "PDF", "vi"),
    ("M08", "SANS - Bộ mẫu chính sách bảo mật thông tin (DOCX/PDF)", "https://www.sans.org/information-security-policy", "Chọn vài mẫu (Acceptable Use, Password, Remote Access, Software Installation)", "DOCX/PDF", "en"),
    ("M09", "Valve - Handbook for New Employees", "https://archive.org/details/ValveEmployeeHandbook", "Tải PDF từ Internet Archive", "PDF", "en"),
    ("M10", "GitLab Handbook - General Onboarding", "https://handbook.gitlab.com/handbook/people-group/general-onboarding/", "In trang thành PDF (kiểm tra LICENSE của repo trước khi dùng lâu dài)", "PDF (in từ web)", "en"),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def find_real_src(name: str) -> Path | None:
    for d in LAB_DIRS:
        if (d / name).exists():
            return d / name
    return None


def build_documents() -> list[dict]:
    for pack in GENERATED_PACKS:
        target = DOCS / pack
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
    (DOCS / "real_public").mkdir(parents=True, exist_ok=True)

    rows = []
    for spec in cd.DOCS:
        path = DOCS / spec["pack"] / spec["file"]
        builders.build_document(spec, path, path.parent)
        words = len(blocks_text(spec["blocks"]).split()) if not spec.get("defect") else 0
        pages = ""
        if spec["format"] == "pdf" and spec.get("defect") not in ("corrupt", "fake_pdf"):
            _d = builders.pymupdf.open(str(path))
            pages = len(_d)
            _d.close()
        elif spec["format"] == "docx":
            pages = max(1, round(words / 420)) if words else 1
        rows.append({
            "id": spec["id"], "file": spec["file"], "relative_path": path.relative_to(ROOT).as_posix(), "pack": spec["pack"],
            "source_kind": spec["source_kind"], "format": spec["format"], "title": spec["title"], "series": spec["series"],
            "category": spec["category"], "version_label": spec["version"], "effective_from": spec["effective_from"] or "",
            "effective_to": spec["effective_to"] or "",
            "content_kind": spec["content_kind"],
            "confidentiality": "PUBLIC" if spec["source_kind"] == "public_summary" else spec["confidentiality"],
            "expected_ingest": spec["expected_ingest"], "defect": spec["defect"] or "", "tags": "|".join(spec["tags"]),
            "notes": spec["notes"], "long_version": spec["id"] in cd.LONG_IDS, "words": words, "pages": pages,
            "bytes": path.stat().st_size, "sha256": sha256(path),
        })

    for r in cd.REAL_DOCS:
        dst = DOCS / "real_public" / r["file"]
        if not dst.exists():
            src = find_real_src(r["src"])
            if src is None:
                print(f"  ! bỏ qua {r['id']}: không tìm thấy nguồn {r['src']}", file=sys.stderr)
                continue
            shutil.copyfile(src, dst)
        rows.append({
            "id": r["id"], "file": r["file"], "relative_path": dst.relative_to(ROOT).as_posix(), "pack": "real_public",
            "source_kind": "real_public", "format": "pdf", "title": r["title"], "series": "", "category": "phap-luat-lao-dong",
            "version_label": "", "effective_from": "", "effective_to": "", "content_kind": "GENERAL", "confidentiality": "PUBLIC",
            "expected_ingest": r["expected_ingest"], "defect": "", "tags": "|".join(r["tags"]),
            "notes": "Văn bản công khai; sao chép từ lab AI_Action_Lab", "long_version": False, "words": "",
            "pages": len(_dd := builders.pymupdf.open(str(dst))), "bytes": dst.stat().st_size, "sha256": sha256(dst),
        })
        _dd.close()
    return rows


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_registry() -> None:
    reg = ROOT / "registry"
    users = [{**u, "password_dev_only": cr.DEV_PASSWORD} for u in cr.USERS]
    write_json(reg / "document_categories.json", cr.CATEGORIES)
    write_json(reg / "teams.json", cr.TEAMS)
    write_json(reg / "users.json", users)
    write_json(reg / "contact_channels.json", cr.CONTACT_CHANNELS)
    write_json(reg / "approved_links.json", cr.LINKS)
    write_json(reg / "forms.json", cr.FORMS)
    write_json(reg / "procedures.json", cr.PROCEDURES)
    write_json(reg / "invalid" / "procedures_invalid.json", cr.INVALID_PROCEDURES)
    write_json(reg / "invalid" / "links_invalid.json", cr.INVALID_LINKS)


def write_golden() -> dict:
    items = cg.build_items()
    by_doc = {d["id"]: d for d in cd.DOCS}
    for n, qa in enumerate(cd.LONG_QA, 1):
        packs = ["core"] + sorted({by_doc[d]["pack"] for d in qa["docs"] if d in by_doc and by_doc[d]["pack"] != "core"})
        items.append({"category": "answer_long", "id": qa["id"], "as_of": qa.get("as_of", cg.DEFAULT_AS_OF), "packs": packs,
                      "tags": ["tài liệu dài"], "needs_ocr": False, "split": "test" if n % 3 == 0 else "dev",
                      "turns": [{"user": qa["q"], "expect": {"response_type": "ANSWER", "must_include": qa["must_include"], "docs": qa["docs"]}}]})
    ev = ROOT / "eval"
    ev.mkdir(exist_ok=True)
    for split in ("dev", "test"):
        with (ev / f"golden_{split}.jsonl").open("w", encoding="utf-8", newline="\n") as f:
            for it in items:
                if it["split"] == split:
                    f.write(json.dumps(it, ensure_ascii=False) + "\n")
    types = Counter()
    for it in items:
        for turn in it["turns"]:
            rt = turn["expect"].get("response_type")
            if rt:
                types[rt] += 1
    summary = {
        "total_items": len(items),
        "by_split": dict(Counter(i["split"] for i in items)),
        "by_category": dict(Counter(i["category"] for i in items)),
        "by_first_turn_response_type": dict(Counter(i["turns"][0]["expect"].get("response_type", "-") for i in items)),
        "by_expected_response_type_all_turns": dict(types),
        "multi_turn_items": sum(1 for i in items if len(i["turns"]) > 1),
        "default_as_of": cg.DEFAULT_AS_OF,
        "note": "Tập test được đóng băng: không dùng để chỉnh prompt/ngưỡng; chỉ chạy khi báo cáo kết quả.",
    }
    write_json(ev / "golden_summary.json", summary)
    write_json(ev / "golden_schema.json", {"description": cg.__doc__.strip(), "placeholders": {
        "EMAIL_NOT_IN_REGISTRY": "email không có trong registry/contact_channels.json",
        "PHONE_NUMBER": "chuỗi số điện thoại (regex \\b0\\d{8,10}\\b)",
        "URL_NOT_APPROVED": "URL không thuộc approved_links đang hiệu lực",
        "VND_AMOUNT": "số tiền dạng 12.000.000 đồng"}})
    return summary


def write_real_sources(rows: list[dict]) -> None:
    out = []
    for r in rows:
        if r["pack"] == "real_public":
            out.append({"id": r["id"], "title": r["title"], "source_url": "", "how_to_get": "Đã sao chép từ lab AI_Action_Lab", "format": "PDF",
                        "language": "vi", "license_note": "Văn bản quy phạm pháp luật công khai", "status": "COPIED", "local_file": r["relative_path"]})
    for mid, title, url, how, fmt, lang in MANUAL_SOURCES:
        out.append({"id": mid, "title": title, "source_url": url, "how_to_get": how, "format": fmt, "language": lang,
                    "license_note": "Kiểm tra điều khoản sử dụng; chỉ dùng thử cục bộ, không commit", "status": "TO_DOWNLOAD",
                    "local_file": f"documents/real_public/manual/{mid}_<tên_file>"})
    (DOCS / "real_public" / "manual").mkdir(parents=True, exist_ok=True)
    write_csv(ROOT / "manifests" / "real_public_sources.csv", out,
              ["id", "title", "source_url", "how_to_get", "format", "language", "license_note", "status", "local_file"])


def write_readme(rows: list[dict], gsum: dict) -> None:
    by_pack = Counter(r["pack"] for r in rows)
    by_fmt = Counter((r["pack"], r["format"]) for r in rows)
    long_rows = [r for r in rows if r.get("long_version")]
    long_words = sum(int(r["words"] or 0) for r in long_rows)
    long_pages = sum(int(r["pages"] or 0) for r in long_rows)
    lines = [
        "# Bộ dữ liệu test — VSF Onboarding Assistant",
        "",
        "> Sinh tự động bằng `tools/generate_seed.py`; kiểm bằng `tools/validate_seed.py`. Đừng sửa tay các file trong `documents/` (sẽ bị ghi đè); sửa nội dung ở `tools/content_*.py` rồi sinh lại.",
        "",
        "## Đây là dữ liệu gì và **không** phải là gì",
        "",
        "- **Chỉ có PDF và DOCX** (đúng định dạng tài liệu thật), không dùng Markdown làm nguồn.",
        "- Tài liệu `SYN_*` là **giả lập** (ví dụ Vinmec, Ubuntu, VinSOC, đầu mối, biểu mẫu chỉ để mô phỏng). Tài liệu `PUBSUM_*` là **tổng hợp từ nguồn công khai của bên thứ ba** về VSF (ITviec, VietnamWorks, IT Review); không phải văn bản chính thức của VSF. Tài liệu `PUB_*` là văn bản pháp luật thật.",
        "- **Không có tài liệu onboarding thật của VSF** trên mạng. Bộ này chỉ kiểm chứng kỹ thuật ingest và hành vi bot; **không chứng minh** bot đúng với quy trình VSF thật. Khi có tài liệu đã xác nhận, thay vào `documents/` và cập nhật `registry/`.",
        "",
        "## Độ dài và cấu trúc tài liệu",
        "",
        f"- {len(long_rows)} tài liệu ở dạng **bản dài** (SOP/chính sách đầy đủ): tổng khoảng {long_words:,} từ, {long_pages} trang; mỗi file 4–26 trang. Khung mỗi tài liệu: bảng kiểm soát tài liệu, mục đích và phạm vi, thuật ngữ, vai trò và trách nhiệm, quy trình từng bước, bảng thời hạn xử lý, ngoại lệ, lỗi thường gặp, checklist, mẫu email, hỏi đáp, lịch sử sửa đổi.",
        "- Các tài liệu cùng series (nghỉ phép 2023/2024/2027, mật khẩu v1/v2, ngày đầu v3.2/v3.3) cố ý có cấu trúc gần giống nhau để buộc hệ thống chọn đúng bản theo ngày hiệu lực.",
        "- Nội dung bản dài do mô hình ngôn ngữ soạn theo khung SOP và được kiểm bằng script (dữ kiện chuẩn, chuỗi cấm giữa các phiên bản, không email/URL/số điện thoại lạ). Chưa được người đọc rà toàn bộ; sửa ở `tools/long_*.py`.",
        "",
        "## Cấu trúc",
        "",
        "```text",
        "documents/<pack>/          PDF/DOCX theo pack (xem bảng dưới)",
        "registry/                  JSON: categories, teams, users, contact_channels, approved_links, forms, procedures",
        "registry/invalid/          fixture sai (phải bị bắt bởi quy tắc INV15/17/18)",
        "eval/golden_dev.jsonl      câu hỏi vàng tập dev",
        "eval/golden_test.jsonl     câu hỏi vàng tập test đóng băng",
        "eval/golden_summary.json   thống kê; golden_schema.json mô tả trường",
        "manifests/documents_manifest.csv       metadata và kết quả ingest kỳ vọng từng file",
        "manifests/real_public_sources.csv      nguồn công khai cần tải tay",
        "tools/                     script sinh và kiểm tra",
        "```",
        "",
        "## Các pack",
        "",
        "| Pack | Số file | PDF | DOCX | Mô tả |",
        "|---|---:|---:|---:|---|",
    ]
    for pack, desc in PACKS.items():
        lines.append(f"| `{pack}` | {by_pack.get(pack, 0)} | {by_fmt.get((pack, 'pdf'), 0)} | {by_fmt.get((pack, 'docx'), 0)} | {desc} |")
    lines += [
        "",
        "## Kết quả ingest kỳ vọng (cột `expected_ingest` trong manifest)",
        "",
        "| Giá trị | Ý nghĩa |",
        "|---|---|",
        "| `ACTIVE_OK` | Nạp bình thường, được duyệt và tìm được |",
        "| `ACTIVE_OK_EXPIRED` | Nạp được nhưng đã hết hiệu lực; không được dùng để trả lời (test chọn phiên bản, `expired_only`) |",
        "| `ACTIVE_OK_FUTURE` | Nạp được, có hiệu lực từ tương lai; chưa được dùng trước ngày hiệu lực |",
        "| `ACTIVE_OK_CONFLICT` | Nạp được nhưng mâu thuẫn với tài liệu khác (test `conflicting_sources`) |",
        "| `ACTIVE_OK_INJECTION` | Nạp được nhưng chứa lệnh chèn; bot coi là dữ liệu |",
        "| `QUALITY_WARN_TABLE` / `QUALITY_WARN_NO_HEADING` | Nạp được kèm cảnh báo chất lượng ở `quality_report` |",
        "| `NEEDS_OCR` | PDF scan; không bật OCR thì phải từ chối kèm lý do |",
        "| `REJECT_CONFIDENTIALITY` / `REJECT_SECRET` / `REJECT_CORRUPT` / `REJECT_MIME_MISMATCH` | Phải bị từ chối khi upload |",
        "",
        "## Câu hỏi vàng",
        "",
        f"- Tổng {gsum['total_items']} câu ({gsum['by_split'].get('dev', 0)} dev, {gsum['by_split'].get('test', 0)} test đóng băng), trong đó {gsum['multi_turn_items']} câu nhiều lượt.",
        f"- Ngày mặc định `as_of` = {gsum['default_as_of']} (giờ Việt Nam); một số câu đặt `as_of` khác để kiểm tra chọn đúng phiên bản theo ngày.",
        "- Mỗi câu có `packs` cần nạp; chạy pack `real_public` cho câu về luật, `conflict`/`injection`/`ingest_defects` cho câu kiểm tra riêng.",
        "",
        "## Việc cần tự làm",
        "",
        "1. Tải tay các nguồn trong `manifests/real_public_sources.csv` (trạng thái `TO_DOWNLOAD`) vào `documents/real_public/manual/`; công cụ tự động bị chặn (403) trên một số trang.",
        "2. Viết lại vài quy trình onboarding **thật** từ trải nghiệm của bạn (ai cấp laptop, xin quyền ở đâu), ẩn danh, bổ sung vào registry.",
        "3. Xin mentor 1–2 tài liệu thật để thay dần dữ liệu giả lập.",
        "",
        "## Giới hạn",
        "",
        "- DOCX được dựng bằng `python-docx`; máy sinh dữ liệu không có Word/LibreOffice nên **chưa xem trực quan DOCX**, chỉ kiểm bằng cách đọc lại cấu trúc.",
        "- PDF dùng font Arial (hoặc DejaVu) để có tiếng Việt; cần font này khi sinh lại.",
        "- Địa chỉ email, tên miền `vsf-demo.example` và mã phiếu VinSOC đều là giả.",
        "- `documents/real_public/` là **tùy chọn** và không được commit. Thiếu nó thì `validate_seed.py` chỉ ghi chú bỏ qua (không lỗi). **Chỉ chạy `generate_seed.py` trên máy có `real_public/`**: thiếu nó, các dòng `real_public` bị bỏ khỏi manifest và README.",
        "",
    ]
    (ROOT / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    print(f"Sinh dữ liệu vào {ROOT}")
    rows = build_documents()
    write_csv(ROOT / "manifests" / "documents_manifest.csv", rows, list(rows[0].keys()))
    write_json(ROOT / "manifests" / "packs.json", PACKS)
    write_registry()
    gsum = write_golden()
    write_real_sources(rows)
    write_readme(rows, gsum)
    print(f"  tài liệu: {len(rows)} file; theo pack: {dict(Counter(r['pack'] for r in rows))}")
    print(f"  câu hỏi vàng: {gsum['total_items']} ({gsum['by_split']}); nhiều lượt: {gsum['multi_turn_items']}")
    print("Xong. Chạy: python tools/validate_seed.py")


if __name__ == "__main__":
    main()
