"""Chỗ cắm rerank (cross-encoder) cho tương lai — HIỆN CHƯA BẬT.

Quyết định không dùng rerank cho MVP đã có sẵn từ trước (D5,
`P-040/docs/PlaningForOptimize/srs/chatbot-vsf/vsf-onboarding-assistant-system-design.md`): "chưa dùng ở
MVP (lab không chứng minh lợi ích, tốn độ trễ); bật `bge-reranker-v2-m3` khi đo thấy Recall@5 chưa đạt".
Xem docs/chatbot-vsf/plan/phase-2/2-e-prompt-guardrail-rerank/01-retrieval-rerank.md.

Hàm này là passthrough để `search_to_sections` gọi đúng đủ 3 bước (search → rerank → done) mà không phải
sửa lại chỗ gọi khi bật rerank thật sau này.
"""

from __future__ import annotations

from src.services.retrieval.hybrid_search import SectionEvidence


def rerank(sections: list[SectionEvidence], *, query: str) -> list[SectionEvidence]:  # noqa: ARG001
    return sections
