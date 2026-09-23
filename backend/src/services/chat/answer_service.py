"""Sinh câu trả lời nhiều ý (`claims[]`) từ evidence đã tìm được cho từng câu hỏi con — mục 6, kế hoạch
2-C/2-D mở rộng. Một lời gọi LLM DUY NHẤT cho toàn bộ câu hỏi (kể cả nhiều ý), không phải 1 lời gọi/ý.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from src.infrastructure.ai.chat_completion_port import ChatCompletionPort
from src.services.chat.guardrail_input import INJECTION_DEFENSE_NOTE
from src.services.chat.prompt_builder import build_user_prompt
from src.services.retrieval.hybrid_search import SectionEvidence

SYSTEM_PROMPT = f"""Bạn là trợ lý onboarding nội bộ, CHỈ trả lời dựa trên các đoạn tài liệu được cung cấp
cho từng câu hỏi (mỗi câu hỏi nằm trong tag <question>, đoạn tài liệu tương ứng nằm trong tag <context>
ngay trước nó). Với MỖI câu hỏi, trả về đúng một claim:
- Có đủ căn cứ: response_type="ANSWER". "text" là câu trả lời ngắn gọn. "quote" là MỘT câu trích NGUYÊN
  VĂN (không đổi một chữ nào) lấy từ đúng một đoạn tài liệu đã cung cấp cho câu hỏi đó. "chunk_id" là mã
  đoạn (ghi kèm đầu mỗi đoạn, dạng "chunk_id=...") chứa câu trích đó.
- Không đoạn nào trả lời được: response_type="NO_BASIS", reason_code="no_evidence", "text"/"quote"/
  "chunk_id" đều là null.
- Câu hỏi về thông tin cá nhân (mentor, chỗ ngồi, lương, số dư phép riêng của người hỏi...) không bao giờ
  có trong tài liệu chính sách chung: response_type="NO_BASIS", reason_code="out_of_scope".
TUYỆT ĐỐI không suy diễn ngoài đoạn tài liệu được cung cấp. {INJECTION_DEFENSE_NOTE}
Chỉ trả JSON đúng schema, không giải thích gì thêm:
{{"claims": [{{"question": "...", "response_type": "ANSWER"|"NO_BASIS",
"reason_code": null|"no_evidence"|"out_of_scope", "text": "..."|null, "quote": "..."|null,
"chunk_id": 123|null}}]}}"""


@dataclass(frozen=True)
class QuestionEvidence:
    question: str
    sections: list[SectionEvidence]


@dataclass(frozen=True)
class Claim:
    question: str
    response_type: str  # "ANSWER" | "NO_BASIS"
    reason_code: str | None
    text: str | None
    quote: str | None
    chunk_id: int | None


async def answer_with_claims(items: list[QuestionEvidence], llm: ChatCompletionPort) -> list[Claim]:
    if not items:
        return []
    # Không có evidence cho BẤT KỲ câu hỏi con nào: khỏi gọi LLM, trả "chưa có căn cứ" ngay (tiết kiệm chi
    # phí, đúng nguyên tắc gốc của phase-2.md).
    if all(not item.sections for item in items):
        return [Claim(item.question, "NO_BASIS", "no_evidence", None, None, None) for item in items]

    raw = await llm.complete_json(system_prompt=SYSTEM_PROMPT, user_prompt=build_user_prompt(items))
    try:
        data = json.loads(raw)
        raw_claims = data["claims"]
        if not isinstance(raw_claims, list):
            raise ValueError("claims không phải mảng")
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        return [Claim(item.question, "NO_BASIS", "llm_contract_error", None, None, None) for item in items]

    claims: list[Claim] = []
    for raw_claim in raw_claims:
        if not isinstance(raw_claim, dict):
            continue
        chunk_id = raw_claim.get("chunk_id")
        claims.append(
            Claim(
                question=str(raw_claim.get("question", "")),
                response_type=str(raw_claim.get("response_type", "NO_BASIS")),
                reason_code=raw_claim.get("reason_code"),
                text=raw_claim.get("text"),
                quote=raw_claim.get("quote"),
                chunk_id=int(chunk_id) if isinstance(chunk_id, int | float) else None,
            )
        )

    # LLM có thể bỏ sót một câu hỏi con — bảo đảm mỗi câu hỏi đầu vào có ít nhất một claim.
    answered = {c.question for c in claims}
    for item in items:
        if item.question not in answered:
            claims.append(Claim(item.question, "NO_BASIS", "llm_skipped_question", None, None, None))
    return claims
