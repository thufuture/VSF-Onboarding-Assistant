"""Quy tắc toàn vẹn của registry (tương ứng INV15/17/18 trong tài liệu DB design). Dùng cho validator và có thể tái dùng ở backend.

Mã lỗi: INV15 (link không được phép hiển thị), INV15_URL, INV15_VERIFIED, INV15_SECURITY, INV17 (chồng hiệu lực),
INV18 (ticket_required thiếu form), REF_LINK, REF_CONTACT, REF_FORM.
"""
from __future__ import annotations

from datetime import date


def _d(v):
    return date.fromisoformat(v) if v else None


def in_effect(rec: dict, as_of: str) -> bool:
    a = date.fromisoformat(as_of)
    f, t = _d(rec.get("effective_from")), _d(rec.get("effective_to"))
    return (f is None or f <= a) and (t is None or a <= t)


def link_displayable(link: dict, as_of: str) -> bool:
    return link["status"] == "APPROVED" and in_effect(link, as_of) and not check_link(link)


def check_link(link: dict) -> list[str]:
    errs = []
    if not str(link["url"]).lower().startswith("https://"):
        errs.append("INV15_URL")
    if link["status"] == "APPROVED":
        if not link.get("verified_by") or not link.get("verified_at"):
            errs.append("INV15_VERIFIED")
        if link.get("requires_security_review") and (link.get("security_review") or {}).get("result") != "PASSED":
            errs.append("INV15_SECURITY")
    return errs


def check_procedure(p: dict, links: dict, contacts: dict, forms_active: dict, as_of: str) -> list[str]:
    errs = []
    if p.get("ticket_required") and not p.get("form_code"):
        errs.append("INV18")
    if p.get("form_code") and p["form_code"] not in forms_active:
        errs.append("REF_FORM")
    for step in p["steps"]:
        for k in step.get("link_keys", []):
            if k not in links:
                errs.append("REF_LINK")
            elif not link_displayable(links[k], as_of):
                errs.append("INV15")
        for k in step.get("contact_keys", []):
            if k not in contacts or contacts[k]["status"] != "ACTIVE":
                errs.append("REF_CONTACT")
    return sorted(set(errs))


def check_no_overlap(procs: list[dict]) -> list[str]:
    """Các bản ACTIVE cùng code không được chồng khoảng hiệu lực."""
    by_code: dict[str, list[dict]] = {}
    for p in procs:
        if p["status"] == "ACTIVE":
            by_code.setdefault(p["code"], []).append(p)
    far = date(9999, 12, 31)
    near = date(1, 1, 1)
    for rows in by_code.values():
        for i, a in enumerate(rows):
            for b in rows[i + 1:]:
                a0, a1 = _d(a.get("effective_from")) or near, _d(a.get("effective_to")) or far
                b0, b1 = _d(b.get("effective_from")) or near, _d(b.get("effective_to")) or far
                if a0 <= b1 and b0 <= a1:
                    return ["INV17"]
    return []
