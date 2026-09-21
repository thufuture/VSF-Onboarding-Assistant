# Báo cáo Phase 2 — tiến độ và các checkpoint (cập nhật 21/09/2026)

> Kế hoạch gốc: [phase-2.md](phase-2.md). Kế hoạch bước tiếp theo: [ke-hoach-tiep-theo.md](ke-hoach-tiep-theo.md).
> Nhánh: `phase-2-vertical-slice` (từ `main` sau PR #3). **Đã commit cục bộ, chưa push, chưa mở PR.**
> **Kết luận: 2-A (`0001_core` và model) đã xong và kiểm chứng trên PostgreSQL/ParadeDB thật. Các bước 2-B đến 2-F chưa làm. Đang chờ bạn xem checkpoint CP-2A.**

## 1. Bảng checkpoint

| Checkpoint | Nội dung cần bạn xem | Trạng thái |
|---|---|---|
| **CP-2A** | `0001_core` và 10 model (rủi ro lớn nhất: migration khó sửa về sau) | **Sẵn sàng để xem** |
| CP-U1 | Landing page và trang đăng nhập (vỏ giao diện) | Chưa làm (kế hoạch ở [ke-hoach-tiep-theo.md](ke-hoach-tiep-theo.md)) |
| CP-2B | Nạp `SYN_D03b`: xem section, chunk, embedding trong DB | Chưa làm |
| CP-2C | Kết quả tìm kiếm hybrid với embedding **thật**, trước khi gọi LLM | Chưa làm |
| CP-2D | LLM thật và validator quote | Chưa làm |
| CP-2F | Báo cáo cuối, số đo, giờ công, quyết định hiệu chỉnh lịch | Chưa làm |

## 2. Tiến độ theo bước (theo [phase-2.md](phase-2.md) mục 5)

| Bước | Nội dung | Trạng thái | Ước lượng gốc |
|---|---|---|---|
| **2-A** | `0001_core` + model | **Xong** (commit `68c3cb0`) | ≈ 0,75 ngày |
| 2-B | Nạp tài liệu: parse, section, chunk, tách từ, embedding, ghi DB | Chưa | ≈ 0,75 ngày |
| 2-C | Tìm kiếm hybrid | Chưa | ≈ 0,5 ngày |
| 2-D | LLM, hợp đồng JSON, validator | Chưa | ≈ 0,5 ngày |
| 2-E | Endpoint và trang chat | Chưa | ≈ 0,25 ngày |
| 2-F | Đo, báo cáo, cập nhật tài liệu | Chưa | ≈ 0,25 ngày |

**Giờ công thật của 2-A:** chưa đo chính xác (làm liền mạch trong một phiên, không bấm giờ). Từ 2-B sẽ ghi giờ từng bước để hiệu chỉnh lịch ở 2-F, đúng yêu cầu của master-plan.

## 3. Đã làm ở 2-A

| Nhóm | Nội dung |
|---|---|
| Model (`backend/src/model/`) | 10 thực thể, mỗi thực thể một file: `user`, `team`, `team_member`, `document_category`, `document`, `document_version`, `document_section`, `document_chunk`, `job`, `audit_log`; cộng `enums.py` (trạng thái là `VARCHAR` + `CHECK`, không dùng native enum) và `base.py` (naming convention, kiểu `Vector(1024)`, hàm dựng cột dùng chung); `__init__.py` import đủ để Alembic thấy hết |
| Migration | `backend/alembic/versions/0001_core.py`: tạo extension (`vector`, `pg_search`, `btree_gist`), 10 bảng, chỉ mục, ràng buộc. Autogenerate rồi chỉnh tay phần đặc biệt (extension, tên ràng buộc loại trừ) |
| Ràng buộc quan trọng | INV1: `EXCLUDE USING gist` chống hai bản `ACTIVE` chồng ngày; INV5: `UNIQUE (document_id, version_label)`; INV9: `confidentiality` chỉ `PUBLIC`/`INTERNAL`; INV10: khóa idempotency duy nhất cho job `PENDING`/`RUNNING`; INV12: ngày hiệu lực hợp lệ; INV14: `UNIQUE (version_id, chunk_index)` và `(version_id, section_index)`; email duy nhất không phân biệt hoa thường |
| Chỉ mục tìm kiếm | HNSW `vector_cosine_ops` (`m=16`, `ef_construction=64`) và BM25 (`pg_search`, `key_field='id'`) trên `document_chunks` |
| Phụ thuộc | Thêm `pgvector` vào `requirements.txt` |
| Test | 10 test tích hợp mới trong `tests/integration/test_core_schema.py`; `conftest.py` tự chạy `alembic upgrade head` cho DB test |

## 4. Kiểm chứng (trên PostgreSQL/ParadeDB thật, `paradedb:v0.25.4-pg16`)

| Kiểm | Kết quả |
|---|---|
| `alembic upgrade head` | Qua |
| `alembic downgrade base` rồi `upgrade head` | Qua (chạy lại được) |
| `alembic check` | **Sạch** ngay lần đầu, kể cả chỉ mục HNSW và BM25 |
| `pytest` | **36 test qua** (26 cũ + 10 mới; 12 test tích hợp) |
| `ruff check`, `ruff format --check`, `mypy` (strict) | Sạch |
| `docker compose up --build backend` | Backend khỏe; `/api/v1/ready` báo `migration: head=["0001"], current=["0001"]` và cả ba extension |

Các test ràng buộc chứng minh: hai bản `ACTIVE` chồng ngày bị **từ chối**; ngày rời nhau và bản `ARCHIVED` chồng ngày được chấp nhận; hai bản `ACTIVE` đều không có ngày (không giới hạn) bị coi là chồng; nhãn phiên bản và số revision trùng bị từ chối; ngày sai thứ tự bị từ chối; tài liệu mức "SECRET" bị từ chối; email khác hoa thường vẫn trùng; hai job hoạt động cùng khóa bị từ chối trong khi job đã xong thì không; vector 1024 chiều lưu và xếp hạng theo cosine đúng, vector sai chiều bị từ chối; hai chỉ mục HNSW và BM25 tồn tại.

**Chưa kiểm chứng:** CI trên GitHub (cần push nhánh); cú pháp **truy vấn** BM25 của `pg_search 0.25.4` (mới kiểm chỉ mục tồn tại; truy vấn là bước thử 30 phút ở 2-C).

## 5. Sai lệch so với kế hoạch và điểm bạn nên xem ở CP-2A

| # | Nội dung | Vì sao | Cần bạn quyết? |
|---|---|---|---|
| 1 | Sửa `NAMING_CONVENTION` trong `base.py`: chỉ mục và ràng buộc duy nhất dùng `column_0_N_name` (nhiều cột), thêm khóa `ex` cho ràng buộc loại trừ | Khớp database-design mục 5; chưa có migration nên sửa được | Không |
| 2 | Trạng thái dùng `CheckConstraint` viết tay qua hàm `check_in(...)` thay vì `Enum(native_enum=False)` | Tên ràng buộc rõ ràng, cùng kết quả trong DB | Không |
| 3 | `team_members` có khóa ngoại `RESTRICT` tới `teams` và `users` | Bảng "Khóa ngoại và hành vi xóa" của database-design không liệt kê hàng này; chọn `RESTRICT` cho đồng nhất với nguyên tắc không xóa cứng | **Có**: nếu muốn xóa thành viên khi xóa đội, đổi sang `CASCADE` **trước khi** áp dụng `0001` ở môi trường thật |
| 4 | `downgrade()` **không** xóa extension | Extension có sẵn trong image, xóa có thể ảnh hưởng dữ liệu khác | Không |
| 5 | Migration tạo cả `pg_search` | Image đã cài sẵn; `CREATE EXTENSION IF NOT EXISTS` an toàn | Không |
| 6 | Cột `embedding` cho phép NULL | Ghi chunk trước, embed sau khi cần retry; INV7 lọc theo `embedding_model_version` | Không |

**Lưu ý cho lần triển khai thật:** vì `0001_core` chưa áp dụng ở môi trường nào ngoài máy bạn và CI, đây là lúc cuối cùng sửa nó mà không cần migration mới. Nếu bạn muốn đổi gì (tên cột, độ dài, khóa ngoại), hãy nói **trước khi** đẩy nhánh lên `main` và triển khai.

## 6. Việc theo dõi (không chặn)

- **Cảnh báo `mypy`/ruff cho migration:** `alembic/versions/*.py` được ruff định dạng lại (dấu nháy kép); các migration sau nên chạy `ruff format` trước khi commit.
- **`tests/integration/conftest.py` chạy `alembic` bằng subprocess:** cần biến `VSF_TEST_DATABASE_URL`; CI đã có sẵn (cùng DB với bước `alembic upgrade head` của `verify.yml`).
- **Tài liệu cần cập nhật ở 2-F:** `README.md` (cách nạp tài liệu), `master-plan.md` và `plan/README.md` (trạng thái Phase 2), tài liệu DB nếu `0001_core` lệch thiết kế (hiện chưa lệch đáng kể).
- **Landing (Phase 10) và giao diện đăng nhập (Phase 4)** được đưa lên làm sớm theo yêu cầu của bạn; khi xong cần cập nhật lại master-plan (xem [ke-hoach-tiep-theo.md](ke-hoach-tiep-theo.md) mục 6).

## 7. Bước tiếp theo

Xem [ke-hoach-tiep-theo.md](ke-hoach-tiep-theo.md): làm song song hai luồng (giao diện landing/đăng nhập/chat giả và backend nạp tài liệu, tìm kiếm, LLM), mỗi luồng có checkpoint riêng.
