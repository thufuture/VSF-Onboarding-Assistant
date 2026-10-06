"""Viga của nhân viên: công cụ lộ trình tất định, LLM định tuyến, hội thoại lưu DB (plan-portal/ingest-tai-lieu-va-tao-task-bang-ai.md mục 6.2, 15, 17).

Gồm cả bộ máy hỏi đáp tài liệu có kiểm chứng (trước đây ở `services/chat`, đã gộp vào đây): `pipeline.run_document_qa` (viết lại câu hỏi, tìm kiếm, trả lời kèm trích dẫn, kiểm nguyên văn), `query_rewrite`, `answer_service`, `prompt_builder`, `validator`, `guardrail_input`, `chat_throttle`.
"""
