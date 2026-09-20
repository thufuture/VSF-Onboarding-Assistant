"""Kiểm tra bộ dữ liệu test: file, định dạng thật, chữ trích được, nhãn nguồn, câu hỏi vàng và toàn vẹn registry.

Chạy:  python tools/validate_seed.py      (thoát mã 1 nếu có lỗi)
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import content_documents as cd  # noqa: E402
import content_facts as cf  # noqa: E402
import registry_rules as rules  # noqa: E402

try:
    import pymupdf
except ImportError:  # pragma: no cover
    import fitz as pymupdf
from docx import Document as Docx  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ERRORS: list[str] = []
NOTES: list[str] = []
OPTIONAL_MISSING: set[str] = set()  # id tài liệu real_public không có mặt (không commit, tùy chọn)
SPEC = {d["id"]: d for d in cd.DOCS}
MIN_WORDS_OF = {d["id"]: d.get("min_words", 0) for d in cd.DOCS}


def err(msg: str) -> None:
    ERRORS.append(msg)


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).lower()


def load_json(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def pdf_text(path: Path) -> str:
    doc = pymupdf.open(str(path))
    try:
        return "\n".join(p.get_text() for p in doc)
    finally:
        doc.close()


def docx_text(path: Path) -> tuple[str, str]:
    d = Docx(str(path))
    parts = [p.text for p in d.paragraphs]
    for t in d.tables:
        for row in t.rows:
            parts.extend(c.text for c in row.cells)
    footer = " ".join(p.text for p in d.sections[0].footer.paragraphs)
    return "\n".join(parts), footer


def spec_text(spec: dict) -> str:
    out = [spec["title"]]
    for kind, *rest in spec["blocks"]:
        if kind in ("h1", "h2", "p"):
            out.append(rest[0])
        elif kind in ("bullets", "numbered"):
            out.extend(rest[0])
        elif kind == "table":
            out.extend(rest[0]["header"])
            for r in rest[0]["rows"]:
                out.extend(r)
    return "\n".join(out)


# --------------------------------------------------------------------------- 1. tài liệu
def check_documents() -> dict[str, str]:
    """Trả về map id -> văn bản (đã chuẩn hóa) để kiểm chéo câu hỏi vàng."""
    texts: dict[str, str] = {}
    manifest = list(csv.DictReader((ROOT / "manifests" / "documents_manifest.csv").open(encoding="utf-8-sig")))
    seen_ids = set()
    for r in manifest:
        rid = r["id"]
        if rid in seen_ids:
            err(f"manifest: id trùng {rid}")
        seen_ids.add(rid)
        path = ROOT / r["relative_path"]
        if not path.exists():
            if r["source_kind"] == "real_public":
                # real_public không được commit: thiếu tệp là bình thường, bỏ qua kèm ghi chú.
                OPTIONAL_MISSING.add(rid)
                NOTES.append(f"{rid}: real_public không có mặt (không commit), bỏ qua")
            else:
                err(f"{rid}: thiếu file {r['relative_path']}")
            continue
        raw = path.read_bytes()
        if len(raw) != int(r["bytes"]) or hashlib.sha256(raw).hexdigest() != r["sha256"]:
            err(f"{rid}: kích thước/sha256 không khớp manifest (dữ liệu đã bị sửa tay?)")
        spec = SPEC.get(rid)
        defect = (spec or {}).get("defect")
        fmt = r["format"]
        prefix_ok = path.name.startswith({"synthetic": "SYN_", "public_summary": "PUBSUM_", "real_public": "PUB_"}[r["source_kind"]])
        if not prefix_ok:
            err(f"{rid}: tiền tố tên file không khớp source_kind {r['source_kind']}")

        # --- định dạng thật
        if defect == "fake_pdf":
            if raw[:5] == b"%PDF-":
                err(f"{rid}: tệp giả PDF lại có chữ ký PDF")
            texts[rid] = norm(raw.decode("utf-8", "replace"))
            continue
        if defect == "corrupt":
            if raw[:5] != b"%PDF-" or b"%%EOF" in raw[-64:]:
                err(f"{rid}: file hỏng phải có chữ ký PDF nhưng thiếu %%EOF ở cuối")
            texts[rid] = norm(spec_text(spec))
            continue
        if fmt == "pdf":
            if raw[:5] != b"%PDF-":
                err(f"{rid}: không có chữ ký PDF")
                continue
            try:
                text = pdf_text(path)
            except Exception as e:  # noqa: BLE001
                err(f"{rid}: không mở được PDF ({e})")
                continue
            footer = text
        elif fmt == "docx":
            if not zipfile.is_zipfile(path) or "word/document.xml" not in zipfile.ZipFile(path).namelist():
                err(f"{rid}: không phải DOCX hợp lệ")
                continue
            try:
                text, footer = docx_text(path)
            except Exception as e:  # noqa: BLE001
                err(f"{rid}: không mở được DOCX ({e})")
                continue
        else:
            err(f"{rid}: định dạng không hỗ trợ {fmt}")
            continue

        # --- scan: không được có lớp chữ
        if defect == "scan" or r["expected_ingest"] == "NEEDS_OCR":
            if len(text.strip()) > 100:
                err(f"{rid}: đáng lẽ là PDF scan nhưng có {len(text.strip())} ký tự lớp chữ")
            texts[rid] = norm(spec_text(spec)) if spec else ""
            continue
        if len(text.strip()) < 40:
            err(f"{rid}: trích được quá ít chữ ({len(text.strip())} ký tự)")
        texts[rid] = norm(text)

        # --- độ dài, chuỗi cấm, email/URL/số điện thoại lạ (tài liệu do mình sinh)
        if r["source_kind"] != "real_public":
            words = len(text.split())
            need = MIN_WORDS_OF.get(rid, 0)
            if words < need:
                err(f"{rid}: chỉ {words} từ, cần ≥ {need} (tài liệu dài bị ngắn)")
            for bad in cf.FORBIDDEN.get(rid, []):
                if norm(bad) in norm(text):
                    err(f"{rid}: chứa chuỗi cấm '{bad}'")
            flat = re.sub(r"\s+", " ", text)
            for em in re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", flat):
                if not em.rstrip(".").lower().endswith(cf.EMAIL_ALLOW_DOMAINS):
                    err(f"{rid}: email lạ {em}")
            for host in re.findall(r"https?://([^\s/)\]\"',;]+)", flat):
                ok = host.lower().endswith(cf.ALLOWED_URL_HOST_SUFFIXES) or any(host.lower().endswith(h) for h in cf.URL_EXCEPTIONS.get(rid, ()))
                if not ok:
                    err(f"{rid}: URL lạ {host}")
            if re.search(cf.PHONE_PATTERN, flat):
                err(f"{rid}: có chuỗi giống số điện thoại")

        # --- nhãn nguồn và header (chỉ tài liệu do mình sinh)
        if r["source_kind"] == "synthetic":
            if "synthetic" not in norm(footer):
                err(f"{rid}: thiếu nhãn SYNTHETIC ở chân trang")
        elif r["source_kind"] == "public_summary":
            if "nguồn công khai" not in norm(footer):
                err(f"{rid}: thiếu nhãn tổng hợp từ nguồn công khai")
        if r["source_kind"] != "real_public" and r["version_label"]:
            if f"Phiên bản: {r['version_label']}" not in text:
                err(f"{rid}: header thiếu 'Phiên bản: {r['version_label']}'")
            if r["effective_from"]:
                y, m, d = r["effective_from"].split("-")
                if f"Ngày hiệu lực: {d}/{m}/{y}" not in text:
                    err(f"{rid}: header thiếu ngày hiệu lực {d}/{m}/{y}")
        if r["expected_ingest"] == "REJECT_CONFIDENTIALITY" and r["confidentiality"] != "CONFIDENTIAL":
            err(f"{rid}: file bị từ chối do bí mật phải có confidentiality=CONFIDENTIAL")

    # tài liệu có trong spec nhưng thiếu trong manifest
    for sid in SPEC:
        if sid not in seen_ids:
            err(f"{sid}: có trong content_documents nhưng không có trong manifest")
    return texts


# --------------------------------------------------------------------------- 2. registry
def check_registry(manifest_ids: set[str], texts: dict[str, str]):
    cats = {c["slug"] for c in load_json("registry/document_categories.json")}
    teams = {t["code"] for t in load_json("registry/teams.json")}
    contacts = {c["key"]: c for c in load_json("registry/contact_channels.json")}
    links = {l["key"]: l for l in load_json("registry/approved_links.json")}
    forms = load_json("registry/forms.json")
    procs = load_json("registry/procedures.json")
    as_of = "2026-09-20"

    for c in contacts.values():
        if c["team"] not in teams:
            err(f"contact {c['key']}: đội {c['team']} không tồn tại")
    for f in forms:
        if f["team"] not in teams:
            err(f"form {f['code']}: đội {f['team']} không tồn tại")
        keys = [x["key"] for x in f["fields"]]
        if len(keys) != len(set(keys)):
            err(f"form {f['code']}: trường trùng key")
    forms_active = {f["code"]: f for f in forms if f["status"] == "ACTIVE" and rules.in_effect(f, as_of)}
    for k, l in links.items():
        e = rules.check_link(l)
        if e:
            err(f"link {k}: vi phạm {e} (dữ liệu hợp lệ không được vi phạm)")
    for p in procs:
        e = rules.check_procedure(p, links, contacts, forms_active, as_of)
        if e:
            err(f"procedure {p['code']}: vi phạm {e}")
        if p["category"] not in cats:
            err(f"procedure {p['code']}: danh mục {p['category']} không tồn tại")
        if p["responsible_team"] not in teams:
            err(f"procedure {p['code']}: đội {p['responsible_team']} không tồn tại")
        for d in p.get("source_docs", []):
            if d not in manifest_ids:
                err(f"procedure {p['code']}: tài liệu nguồn {d} không có trong manifest")
    if rules.check_no_overlap(procs):
        err("procedures: các bản ACTIVE cùng code chồng hiệu lực")
    for r in cd.DOCS:
        if r["category"] not in cats:
            err(f"tài liệu {r['id']}: danh mục {r['category']} không tồn tại")
    # email đầu mối phải khớp danh bạ trong tài liệu P05
    p05 = texts.get("P05", "")
    for c in contacts.values():
        if c["kind"] == "EMAIL" and c["status"] == "ACTIVE" and c["value"].lower() not in p05:
            err(f"contact {c['key']}: email {c['value']} không xuất hiện trong tài liệu P05 (danh bạ)")

    # fixture sai phải bị bắt đúng
    for case in load_json("registry/invalid/procedures_invalid.json"):
        ps = case["procedures"]
        got = set(rules.check_no_overlap(ps)) if len(ps) > 1 else set(rules.check_procedure(ps[0], links, contacts, forms_active, as_of))
        if got != set(case["expected_errors"]):
            err(f"invalid procedure '{case['case']}': kỳ vọng {case['expected_errors']} nhưng bắt được {sorted(got)}")
    for case in load_json("registry/invalid/links_invalid.json"):
        got = set(rules.check_link(case["link"]))
        if got != set(case["expected_errors"]):
            err(f"invalid link '{case['case']}': kỳ vọng {case['expected_errors']} nhưng bắt được {sorted(got)}")
    return links, contacts, {p["code"]: p for p in procs}


# --------------------------------------------------------------------------- 3. câu hỏi vàng
def procedure_text(p: dict, links: dict, contacts: dict) -> str:
    out = [p["title"], p["trigger_text"], p.get("next_step") or ""]
    for s in p["steps"]:
        out.append(s["text"])
        out.extend(links[k]["label"] for k in s["link_keys"] if k in links)
        for k in s["contact_keys"]:
            if k in contacts:
                out.extend([contacts[k]["label"], contacts[k]["value"]])
    if p.get("form_code"):
        out.append(p["form_code"])
    return "\n".join(out)


def check_golden(manifest: dict[str, dict], texts: dict[str, str], links, contacts, procs) -> dict:
    packs = set(load_json("manifests/packs.json"))
    items = []
    for split in ("dev", "test"):
        for line in (ROOT / "eval" / f"golden_{split}.jsonl").read_text(encoding="utf-8").splitlines():
            it = json.loads(line)
            if it["split"] != split:
                err(f"{it['id']}: split trong file {split} khác trường split")
            items.append(it)
    ids = [i["id"] for i in items]
    for dup, n in Counter(ids).items():
        if n > 1:
            err(f"golden: id trùng {dup}")
    valid_types = {"ANSWER", "GUIDE_PROCESS", "ASK_CLARIFICATION", "OFFER_TICKET", "NO_BASIS", "OUT_OF_SCOPE"}
    valid_reasons = {"no_evidence", "expired_only", "insufficient_evidence", "conflicting_sources"}
    checked_tokens = 0
    for it in items:
        for p in it["packs"]:
            if p not in packs:
                err(f"{it['id']}: pack {p} không tồn tại")
        try:
            from datetime import date
            date.fromisoformat(it["as_of"])
        except ValueError:
            err(f"{it['id']}: as_of không hợp lệ {it['as_of']}")
        if not it["turns"]:
            err(f"{it['id']}: không có lượt nào")
        for ti, turn in enumerate(it["turns"], 1):
            e = turn["expect"]
            where = f"{it['id']}#{ti}"
            rt = e.get("response_type")
            if rt and rt not in valid_types:
                err(f"{where}: response_type lạ {rt}")
            if e.get("reason_code"):
                if rt != "NO_BASIS":
                    err(f"{where}: reason_code chỉ dành cho NO_BASIS")
                if e["reason_code"] not in valid_reasons:
                    err(f"{where}: reason_code lạ {e['reason_code']}")
            if rt == "NO_BASIS" and not e.get("reason_code"):
                err(f"{where}: NO_BASIS thiếu reason_code")
            if rt == "OFFER_TICKET" and not e.get("ticket"):
                err(f"{where}: OFFER_TICKET thiếu ticket kỳ vọng")
            if e.get("offers_ticket") and rt != "GUIDE_PROCESS":
                err(f"{where}: offers_ticket chỉ đi với GUIDE_PROCESS")
            corpus = ""
            skip_tokens = False
            for d in e.get("docs", []):
                m = manifest.get(d)
                if not m:
                    err(f"{where}: tài liệu {d} không có trong manifest")
                    continue
                if m["pack"] not in it["packs"]:
                    err(f"{where}: tài liệu {d} thuộc pack {m['pack']} nhưng câu hỏi không nạp pack đó")
                if d in OPTIONAL_MISSING:
                    # tài liệu real_public tùy chọn không có mặt: bỏ kiểm chuỗi bắt buộc của lượt này
                    skip_tokens = True
                    NOTES.append(f"{where}: bỏ kiểm chuỗi bắt buộc vì thiếu tài liệu tùy chọn {d}")
                    continue
                corpus += "\n" + texts.get(d, "")
            if e.get("procedure"):
                pr = procs.get(e["procedure"])
                if not pr:
                    err(f"{where}: quy trình {e['procedure']} không tồn tại")
                else:
                    corpus += "\n" + norm(procedure_text(pr, links, contacts))
                    tk = e.get("ticket") or {}
                    if pr["ticket_required"] and not (e.get("offers_ticket") or tk):
                        NOTES.append(f"{where}: quy trình {pr['code']} cần ticket nhưng lượt không đánh dấu offers_ticket")
                    if not pr["ticket_required"] and (e.get("offers_ticket") or tk):
                        err(f"{where}: quy trình {pr['code']} không cần ticket nhưng lượt kỳ vọng ticket")
            if e.get("ticket", {}).get("form_code"):
                fc = e["ticket"]["form_code"]
                if not any(f["code"] == fc for f in load_json("registry/forms.json")):
                    err(f"{where}: form {fc} không tồn tại")
            if rt in ("ANSWER", "GUIDE_PROCESS") and corpus and not skip_tokens:
                for tok in e.get("must_include", []):
                    checked_tokens += 1
                    if norm(tok) not in norm(corpus):
                        err(f"{where}: chuỗi bắt buộc '{tok}' không nằm trong tài liệu/quy trình nguồn")
    # độ phủ
    by_cat = Counter(i["category"] for i in items)
    test_cats = {i["category"] for i in items if i["split"] == "test"}
    for c in by_cat:
        if c not in test_cats:
            err(f"golden: nhóm '{c}' không có câu nào trong tập test")
    types = Counter()
    for i in items:
        for t in i["turns"]:
            if t["expect"].get("response_type"):
                types[t["expect"]["response_type"]] += 1
    for rt in valid_types:
        if types[rt] < 5:
            err(f"golden: loại phản hồi {rt} chỉ có {types[rt]} lượt (cần ≥ 5)")
    if not 90 <= len(items) <= 320:
        err(f"golden: tổng {len(items)} câu, kỳ vọng 90–320")
    return {"items": len(items), "by_category": dict(by_cat), "types": dict(types), "tokens_checked": checked_tokens,
            "dev": sum(1 for i in items if i["split"] == "dev"), "test": sum(1 for i in items if i["split"] == "test"),
            "multi_turn": sum(1 for i in items if len(i["turns"]) > 1)}


def main() -> int:
    for rel in ("manifests/documents_manifest.csv", "eval/golden_dev.jsonl", "eval/golden_test.jsonl", "registry/procedures.json"):
        if not (ROOT / rel).exists():
            print(f"Thiếu {rel}. Chạy python tools/generate_seed.py trước.")
            return 2
    manifest_rows = list(csv.DictReader((ROOT / "manifests" / "documents_manifest.csv").open(encoding="utf-8-sig")))
    manifest = {r["id"]: r for r in manifest_rows}
    texts = check_documents()
    links, contacts, procs = check_registry(set(manifest), texts)
    g = check_golden(manifest, texts, links, contacts, procs)

    print("== Tài liệu ==")
    by = Counter((r["pack"], r["format"]) for r in manifest_rows)
    for (pack, fmt), n in sorted(by.items()):
        print(f"  {pack:16s} {fmt:5s} {n}")
    print(f"  tổng {len(manifest_rows)} file")
    print("== Câu hỏi vàng ==")
    print(f"  {g['items']} câu (dev {g['dev']}, test {g['test']}, nhiều lượt {g['multi_turn']}); đã kiểm chéo {g['tokens_checked']} chuỗi bắt buộc với tài liệu/quy trình")
    print(f"  theo nhóm: {g['by_category']}")
    print(f"  theo loại phản hồi (mọi lượt): {g['types']}")
    for n in NOTES:
        print("  ghi chú:", n)
    if ERRORS:
        print(f"\nCÓ {len(ERRORS)} LỖI:")
        for e in ERRORS:
            print("  -", e)
        return 1
    print("\nOK: 0 lỗi")
    return 0


if __name__ == "__main__":
    sys.exit(main())
