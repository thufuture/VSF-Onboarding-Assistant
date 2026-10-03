"""Viết lại/tách câu hỏi thành nhiều câu độc lập trước khi tìm kiếm (mục 5, kế hoạch 2-C/2-D mở rộng).

Giới hạn số/độ dài câu hỏi con (mục 4.3, 2-e-prompt-guardrail-rerank/03-generation-guardrail-tien-kiem.md):
mỗi câu hỏi con tốn thêm 1 lượt embed + 1 lượt tìm kiếm hybrid, và `standalone_questions[]` do LLM sinh ra
không có giới hạn tự nhiên nào — một input ngắn vẫn có thể khiến LLM trả về mảng bất thường dài (lỗi model,
hoặc bị yêu cầu injection "trả về 100 câu hỏi").
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from src.infrastructure.ai.chat_completion_port import ChatCompletionPort
from src.infrastructure.observability.call_metrics import call_context
from src.services.chat.guardrail_input import INJECTION_DEFENSE_NOTE, wrap_user_input

# Không có ca hợp lệ nào trong hỏi-đáp onboarding cần hơn 5 ý trong một câu hỏi (ví dụ đã gặp thực tế: 2 ý).
MAX_SUBQUESTIONS = 5
# Câu hỏi con luôn ngắn hơn câu gốc vì chỉ mang một ý; 300 ký tự đủ rộng cho câu tiếng Việt đầy đủ.
MAX_SUBQUESTION_LENGTH = 300
# Vượt xa ngưỡng hợp lý (khác NHIỀU so với MAX_SUBQUESTIONS) là dấu hiệu LLM lỗi nặng, không phải câu hỏi
# nhiều ý thật — bỏ hẳn kết quả rewrite thay vì chỉ cắt bớt, để không "hợp thức hoá" một phản hồi bất thường.
_ABNORMAL_RESULT_THRESHOLD = 20

SYSTEM_PROMPT = f"""Bạn nhận một câu hỏi của nhân sự mới, có thể gõ tắt, không dấu, hoặc gộp nhiều ý.
Việc của bạn: viết lại thành một hoặc nhiều câu hỏi độc lập, đầy đủ ngữ cảnh, tiếng Việt có dấu, đúng
chính tả. Không suy diễn thêm thông tin không có trong câu hỏi gốc. Nếu câu hỏi chỉ có một ý, trả về
mảng một phần tử (giữ nguyên ý, chỉ sửa chính tả/viết tắt nếu cần). Không bao giờ trả về nhiều hơn
{MAX_SUBQUESTIONS} câu hỏi con.
{INJECTION_DEFENSE_NOTE}
Chỉ trả JSON đúng schema, không giải thích gì thêm:
{{"standalone_questions": ["câu hỏi độc lập 1", "câu hỏi độc lập 2"]}}"""

HISTORY_NOTE = (
    "Nếu có khối <history> (vài lượt hội thoại gần nhất), chỉ dùng nó để hiểu câu hỏi mới đang nối tiếp ý gì "
    '(ví dụ "còn thử việc thì sao?" -> viết lại đủ chủ đề). Không trả lời, không đưa nội dung lịch sử vào câu hỏi '
    "nếu câu mới đã đủ ý."
)
# Mỗi lượt lịch sử cắt ngắn để giữ số token ổn định và không đưa nguyên văn câu trả lời dài vào prompt.
HISTORY_TURN_MAX_CHARS = 300


def _format_history(history: Sequence[tuple[str, str]]) -> str:
    lines = [f"{'Người hỏi' if role == 'USER' else 'Viga'}: {text[:HISTORY_TURN_MAX_CHARS]}" for role, text in history]
    return "<history>\n" + "\n".join(lines) + "\n</history>\n"


async def rewrite_query(
    question: str, llm: ChatCompletionPort, history: Sequence[tuple[str, str]] | None = None
) -> list[str]:
    """Không lưu kết quả vào DB (mục 12.2, kế hoạch) — chỉ dùng tạm trong bộ nhớ cho lượt xử lý này.

    `history`: các cặp (vai, nội dung) của vài lượt gần nhất trong cùng cuộc trò chuyện (mục 6.2), chỉ để hiểu câu nối tiếp.
    """
    fallback = question.strip()
    system_prompt = SYSTEM_PROMPT
    user_prompt = wrap_user_input(question)
    if history:
        system_prompt = f"{SYSTEM_PROMPT}\n{HISTORY_NOTE}"
        user_prompt = _format_history(history) + user_prompt
    with call_context(operation="chat.rewrite"):
        raw = await llm.complete_json(system_prompt=system_prompt, user_prompt=user_prompt)
    try:
        data = json.loads(raw)
        questions = data["standalone_questions"]
        if not isinstance(questions, list):
            raise ValueError("standalone_questions không phải mảng")
        cleaned = [str(q).strip() for q in questions if str(q).strip()]
        if not cleaned:
            raise ValueError("standalone_questions không có câu hỏi hợp lệ nào")
        if len(cleaned) > _ABNORMAL_RESULT_THRESHOLD:
            # Không "hợp thức hoá" một phản hồi bất thường bằng cách cắt bớt — coi như lỗi, lùi về câu gốc.
            raise ValueError(f"standalone_questions bất thường: {len(cleaned)} phần tử")
        limited = [q[:MAX_SUBQUESTION_LENGTH] for q in cleaned[:MAX_SUBQUESTIONS]]
        return limited
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        # LLM trả sai định dạng/bất thường: lùi về dùng nguyên câu hỏi gốc, không chặn cả luồng vì một bước
        # phụ lỗi.
        return [fallback] if fallback else []
