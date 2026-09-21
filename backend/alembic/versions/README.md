# Thư mục migration

Chưa có migration nào ở Phase 1. Alembic cần thư mục này tồn tại nên có tệp này thay cho `.gitkeep`.

Thứ tự theo `docs/chatbot-vsf/vsf-onboarding-assistant-database-design.md` mục 7:

| Migration | Phase |
|---|---|
| `0001_core` | 2 |
| `0002_registry` | 6 |
| `0003_chat`, `0004_tickets` | 7 |

Mỗi migration chỉ áp dụng một lần; không sửa migration đã áp dụng.
