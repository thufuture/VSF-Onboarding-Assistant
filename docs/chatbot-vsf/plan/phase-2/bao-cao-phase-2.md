# Báo cáo Phase 2 — tiến độ và các checkpoint (cập nhật 21/09/2026)

> Kế hoạch gốc: [phase-2.md](phase-2.md). Kế hoạch bước tiếp theo: [ke-hoach-tiep-theo.md](ke-hoach-tiep-theo.md).
> Nhánh: `phase-2-vertical-slice` (từ `main` sau PR #3). **Đã commit cục bộ, chưa push, chưa mở PR.**
> **Kết luận: 2-A (`0001_core` và model), U1 (landing) và U2 (trang đăng nhập, vỏ) đã xong và kiểm chứng. Các bước 2-B đến 2-F và U3 chưa làm. Đang chờ bạn xem CP-2A và CP-U1.**

## 1. Bảng checkpoint

| Checkpoint | Nội dung cần bạn xem | Trạng thái |
|---|---|---|
| **CP-2A** | `0001_core` và 10 model (rủi ro lớn nhất: migration khó sửa về sau) | **Sẵn sàng để xem** |
| **CP-U1** | Landing page và trang đăng nhập (vỏ giao diện): chạy `npm run dev`, mở `/vi` và `/vi/login`; ảnh chụp ở [screenshots/](screenshots/) | **Sẵn sàng để xem** |
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
| **U1** | Landing page (thiết kế lại theo Ralion và VLearn) | **Xong** | ≈ 0,5 ngày |
| **U2** | Trang đăng nhập (vỏ, bố cục Ralion) | **Xong** | ≈ 0,4 ngày |
| U3 | Trang chat giả (`/vi/chat`) | Chưa | ≈ 0,2 ngày |

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

## 3B. Đã làm ở U1 và U2 (giao diện, bản thiết kế lại theo Ralion và VLearn)

> Bản đầu (Tailwind tối giản) bị bạn yêu cầu làm lại: **giao diện phải giống landing và trang đăng nhập của Ralion, hero dùng ảnh Vincom Center Đồng Khởi như VLearn, chỉ đổi nội dung.** Bản dưới là bản đã làm lại. Yêu cầu này thay các quyết định **U-D2** (hero gradient, chưa có ảnh) và **U-D5** (viết lại bằng Tailwind, không chép CSS Ralion).

| Nhóm | Nội dung |
|---|---|
| **U1 Landing** (`frontend/src/features/landing/`) | `LandingPage.tsx` chuyển thể từ landing của Ralion: header cố định (trong suốt trên ảnh, đổi sang nền trắng khi cuộn, mục đang xem được tô sáng), **hero ảnh Vincom Center Đồng Khởi toàn khung + lớp phủ xanh đậm + chữ trắng căn giữa** (như VLearn), dải bốn dịch vụ, phần giới thiệu, **ba tính năng kèm mockup** (hỏi đáp có nguồn, quy trình/link/đầu mối, ticket nháp), bốn vai trò, bảy công nghệ, kêu gọi cuối trang, chân trang. `LandingPage.module.css` chép từ CSS của Ralion (đã bỏ phần video, hero cũ, chọn ngôn ngữ; đổi biến màu và phông) cộng phần hero mới |
| **Ảnh hero** | `public/images/landing/hero-vincom-dong-khoi.webp` (325 KB, cắt 1920×1080), **CC BY-SA 4.0**, tác giả Steffen Schmitz (Wikimedia Commons), giấy phép đã đối chiếu qua API của Commons. Ghi công hiển thị ngay trên hero (tác giả, giấy phép, "đã cắt và nén") và trong `CREDITS.md`; chú thích "Ảnh minh họa" đúng như [landing-page-plan.md](../landing-page-plan.md) mục 4 (trang không nói VSF làm việc ở tòa nhà này) |
| **Nội dung VSF** | Chữ nằm hết trong `messages/vi.json` (khối `landing`), không viết cứng trong component như Ralion. Mockup dùng dữ liệu **có thật trong bộ seed**: quy trình `PR-SOFTWARE-REQUEST` (4 bước, biểu mẫu `IT-SW-01`, đầu mối IT/VinSOC), biểu mẫu `IT-DEV-01`, chính sách nghỉ phép 2024 (12 ngày); ghi rõ "hội thoại minh họa, dữ liệu giả lập". Không có số liệu hiệu quả chưa đo |
| **U2 Đăng nhập** (`frontend/src/features/auth/`, `app/[locale]/login/page.tsx`) | Bố cục Ralion: header có thương hiệu và ba liên kết về landing; **panel trái xanh có cạnh cắt hình mũi tên** (nhãn, tiêu đề, mô tả, ba lợi ích); thẻ đăng nhập bên phải. `LoginPage.module.css` chép từ CSS của Ralion (đã bỏ video, khung "tài khoản test", chọn ngôn ngữ). `LoginForm` giữ logic của tôi (kiểm nhập liệu ở client, đọc `FormData`, gọi `POST /api/v1/auth/login`, `?next=` an toàn, trạng thái đang gửi) nhưng dùng markup và biểu tượng của Ralion |
| Phụ thuộc và phông | Thêm `lucide-react` (icon landing) và `@primer/octicons-react` (icon đăng nhập), đều là phụ thuộc Ralion đã dùng. Phông **Be Vietnam Pro** qua `next/font/google` (tải lúc build, tự host; Poppins của Ralion thiếu ký tự tiếng Việt). Không gọi Google Fonts hay CDN nào khi chạy |
| Không chép từ Ralion | Logo Ralion (thay bằng `VsfBrand`: chữ + biểu tượng bong bóng chat vẽ SVG), video demo và `iframe` Google Drive, khung "tài khoản test" trỏ Google Doc, `LanguageSwitcher` và bản `en`, `X-User-Id`/`localStorage`, biểu tượng công nghệ tải từ CDN bên thứ ba, các liên kết mạng xã hội giả |
| Test giao diện | **74 test** Vitest (Phase 1 có 13): cấu trúc và neo của landing, hero (ảnh, ghi công, nút), dữ liệu mockup, quy tắc nội dung (không %, không nhắc VLearn/VinUni/Ralion, chỉ chú thích ảnh mới nhắc Vincom, không chữ Việt cứng trong component); đăng nhập (định tuyến an toàn, gọi API, form, quét mã nguồn không `ralion`/`X-User-Id`/`localStorage`; CSS không còn video hay liên kết ngoài) |
| Kiểm chứng | `npm run lint`, `typecheck`, `test` (74 qua), `build` xanh. Ảnh chụp thật trên dev server: [hero 1440 px](screenshots/landing-hero-1440.jpg), [landing toàn trang 1440 px](screenshots/landing-full-1440.jpg), [landing 375 px](screenshots/landing-full-375.jpg) (chụp bằng iframe rộng đúng 375 px), [đăng nhập 1440 px](screenshots/login-1440.jpg), [đăng nhập 375 px](screenshots/login-375.jpg). Không tràn ngang |
| Hành vi khi gửi form | `POST /api/v1/auth/login` hiện trả **404** (backend chưa có route, Phase 4): form hiện "Không thể đăng nhập lúc này. Hãy thử lại sau." Đúng hành vi của bản vỏ |

**Chưa kiểm chứng:** Lighthouse; chế độ tối (landing và đăng nhập của Ralion là nền sáng, chưa có công tắc); công tắc ngôn ngữ EN/VI như VLearn (MVP chỉ tiếng Việt nên không làm); bấm gửi form trong trình duyệt thật; Playwright (dời sang Phase 9).

**Lưu ý:** landing mô tả các tính năng theo thiết kế (quy trình, ticket, quản lý tài liệu) nhưng hiện mới có khung; nhãn "Bản demo thực tập" và "hội thoại minh họa, dữ liệu giả lập" nằm trên trang để không gây hiểu nhầm. Build cần mạng để `next/font` tải phông (CI và `publish` đều có mạng).

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

## 5B. Sai lệch so với kế hoạch ở U1/U2

| # | Nội dung | Vì sao |
|---|---|---|
| 1 | Thiết kế **chép từ Ralion** (CSS module, mockup, bố cục), hero dùng **ảnh thật** | Theo yêu cầu của bạn sau khi xem bản đầu; thay các quyết định U-D2 và U-D5 |
| 2 | Thêm hai phụ thuộc (`lucide-react`, `@primer/octicons-react`) và phông qua `next/font/google` | Cần để giữ đúng thiết kế Ralion; Poppins thiếu tiếng Việt nên đổi sang Be Vietnam Pro |
| 3 | Chữ vẫn nằm trong `messages/vi.json` (Ralion viết cứng trong component) | Giữ quy ước i18n của dự án; có test chặn chữ Việt cứng |
| 4 | Không có công tắc ngôn ngữ EN/VI và công tắc chế độ tối như ảnh VLearn | MVP chỉ tiếng Việt (quyết định đã chốt); nền sáng theo Ralion. Có thể thêm sau nếu bạn muốn |
| 5 | Ảnh CC BY-SA 4.0 nên **ảnh** (không phải mã) phải giữ giấy phép này | Đã ghi trong `CREDITS.md` và hiển thị ghi công trên trang |
| 6 | Lighthouse và Playwright chưa làm | U-D6: dời; đã chụp ảnh và kiểm tay thay thế |
| 7 | Bản đầu bạn thấy ở `localhost:3000` không có CSS và hiện nội dung cũ | Không phải lỗi thiết kế: cổng 3000 lúc đó chạy `next start` (bản build cũ) trong khi tôi đã build lại nên tệp CSS cũ biến mất. Bây giờ dev server chạy đúng mã mới |
| 8 | Lần chạy `npx prettier` đầu tiên vô tình định dạng lại một số tệp cũ (dòng 80 cột) | Đã hoàn tác các tệp ngoài phạm vi; repo dùng dòng dài 120 cột, chưa có cấu hình Prettier (nên thêm ở PR riêng) |

## 6. Việc theo dõi (không chặn)

- **Cảnh báo `mypy`/ruff cho migration:** `alembic/versions/*.py` được ruff định dạng lại (dấu nháy kép); các migration sau nên chạy `ruff format` trước khi commit.
- **`tests/integration/conftest.py` chạy `alembic` bằng subprocess:** cần biến `VSF_TEST_DATABASE_URL`; CI đã có sẵn (cùng DB với bước `alembic upgrade head` của `verify.yml`).
- **Tài liệu cần cập nhật ở 2-F:** `README.md` (cách nạp tài liệu), `master-plan.md` và `plan/README.md` (trạng thái Phase 2), tài liệu DB nếu `0001_core` lệch thiết kế (hiện chưa lệch đáng kể).
- **Landing (Phase 10) và giao diện đăng nhập (Phase 4)** được đưa lên làm sớm theo yêu cầu của bạn; khi xong cần cập nhật lại master-plan (xem [ke-hoach-tiep-theo.md](ke-hoach-tiep-theo.md) mục 6).

## 7. Bước tiếp theo

Sau CP-U1: làm luồng backend theo [ke-hoach-tiep-theo.md](ke-hoach-tiep-theo.md): **2-B** (nạp tài liệu), **2-C** (tìm kiếm hybrid, mở đầu bằng spike BM25), **2-D** (LLM và validator), rồi **U3** (chat giả) cùng **2-E** (nối endpoint thật) và **2-F** (đo, báo cáo). Cần khóa DeepSeek và Modal từ 2-B/2-D trở đi (chưa có thì làm bằng giả và ghi "chưa đo").
