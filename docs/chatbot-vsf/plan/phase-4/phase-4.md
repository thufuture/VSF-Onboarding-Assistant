# Phase 4 — Kế hoạch chi tiết: đăng nhập, đăng xuất và trang cho nhân sự mới (chưa thực hiện, chờ bạn duyệt)

> Thuộc [master-plan.md](../master-plan.md), **Phase 4 — Xác thực và trang đăng nhập** [Bắt buộc]; kế thừa [frontend-login-reuse.md](../frontend-login-reuse.md) và [phase-2/bao-cao-phase-2.md](../phase-2/bao-cao-phase-2.md) (giao diện đăng nhập dạng vỏ đã xong).
> Yêu cầu của bạn: **làm luồng đăng nhập và đăng xuất trước, giống mã tham khảo của Ralion, rồi có trang cho người dùng mới ("kỹ sư mới" theo cách gọi của Ralion, **nhân sự mới** theo PRD của VSF) hiện ngay sau khi đăng nhập.**
> Mọi đoạn mã ở đây là **bản dự kiến**. Ước lượng ≈ **1,4 ngày công**.

## 0. Trả lời nhanh: có hợp lý không?

**Có, với ba điều chỉnh.**

| Lý do hợp lý | Điều chỉnh |
|---|---|
| Giao diện đăng nhập đã xong, bảng `users`, `teams`, `team_members`, cột `session_invalid_before` đã có trong `0001_core`; việc còn lại chủ yếu là backend xác thực | **1. Trang sau đăng nhập chỉ làm dạng vỏ** (khung ứng dụng, lời chào, câu hỏi gợi ý, ô chat dữ liệu giả). Chat thật cần lõi của Phase 2 (nạp tài liệu, tìm kiếm, LLM); làm đủ 6 loại phản hồi trước lõi là làm ngược |
| Mọi thứ về sau (chat, tài liệu, ticket) đều cần biết "ai đang hỏi"; làm xác thực sớm tránh phải khóa lại các endpoint tạm (`/api/v1/chat/ask`) | **2. Chỉ chép phần xác thực của Ralion, bỏ phần dự án** (membership, `/select-project`, đổi mật khẩu bắt buộc, tùy chọn giọng điệu chat, header `X-User-Id`): VSF không có khái niệm dự án |
| Chỉ dời lõi Phase 2 khoảng 1,4 ngày, trong khi phần lõi này không phụ thuộc phần xác thực | **3. Quay lại lõi (2-B, 2-C, 2-D) ngay sau Phase 4**; chưa làm quản trị của HR. Khu HR/Admin chỉ có trang giữ chỗ để kiểm điều hướng theo vai trò |

Rủi ro của việc đảo thứ tự: lịch tổng vẫn 4 tuần nhưng **số đo giờ công của Phase 2 (để hiệu chỉnh lịch) đến muộn hơn**; và có thêm bề mặt bảo mật phải kiểm sớm (nên tốt hơn là muộn).

## 1. Ranh giới

| Có trong Phase 4 | **Không** có (thuộc phase khác) |
|---|---|
| `POST /api/v1/auth/login`, `POST /auth/logout`, `GET /auth/me`, `POST /auth/refresh` | Quản lý người dùng bằng giao diện (Phase 8) |
| Băm mật khẩu scrypt, cookie phiên ký HMAC, thu hồi bằng `session_invalid_before`, giới hạn thử sai | Đổi mật khẩu bắt buộc, quên mật khẩu, tự đăng ký, SSO (chưa có trong PRD chuẩn, ngoài 4 tuần) |
| Vai trò `USER`, `HR`, `ADMIN` và kiểm quyền ở tầng `api` | Phân quyền theo tài liệu/bộ phận (PRD: không có ACL tài liệu) |
| Nạp tài khoản dev từ `registry/users.json` (chỉ ngoài production) | Nạp tài khoản thật (do HR/Admin tạo ở Phase 8) |
| Chặn truy cập trang khi chưa đăng nhập, chuyển trang theo vai trò | Playwright (Phase 9); kiểm bằng pytest, Vitest, chụp ảnh |
| **Trang nhân sự mới** `/vi/chat`: khung ứng dụng, đăng xuất, lời chào, câu hỏi gợi ý, chat giả | Chat thật, 6 loại phản hồi, SSE (Phase 2 và 7) |
| Trang giữ chỗ `/vi/admin` cho HR/Admin | Màn hình quản lý tài liệu, registry, ticket (Phase 5 đến 8) |

## 2. Đối chiếu với Ralion (chép, đổi, bỏ)

Nguồn đã đọc: `src/services/session_service.py`, `src/services/auth_service.py`, `src/api/routers/auth_router.py`, `src/api/dependencies.py` và phía frontend `features/auth/session.ts` của Ralion.

| Phần của Ralion | Quyết định | Ghi chú |
|---|---|---|
| **Cookie phiên HMAC** `user_id.issued_at.expires_at.signature`, so sánh bằng `hmac.compare_digest`, kiểm chữ ký trước khi tin trường nào | **Chép, đổi tên cookie** thành `vsf_session` | Đã kiểm chứng ở Ralion; khớp system design mục 8 |
| **`revocation_stamp`**: cắt phần lẻ giây khi ghi `session_invalid_before` | **Chép ý tưởng, đổi kiểu**: cột của VSF là `timestamptz` (Ralion dùng datetime không múi giờ) | Ralion đã gặp lỗi "vừa đổi mật khẩu xong đăng nhập lại vẫn bị đá ra" vì so sánh giây với micro giây; cần test riêng cho ca này |
| **`hash_password`/`verify_password`** scrypt (`n=2^14, r=8, p=1`, định dạng `scrypt$salt$digest`) | **Chép nguyên** | Đúng thiết kế (scrypt); có test |
| **`/auth/login`, `/me`, `/refresh`, `/logout`** | **Chép, đổi hình dạng**: phản hồi theo hợp đồng của `frontend/src/features/auth/session.ts` (`id`, `email`, `display_name`, `role`, `expires_at`); lỗi một hình dạng `{code, message_key, detail}` (system design mục 9) | Thêm `/auth/refresh` vào bảng API của system design |
| **Gia hạn phiên (`refresh`)** khi còn dưới nửa TTL và tab đang mở | **Chép** (quyết định D2) | TTL 30 phút hợp với "TTL ngắn" của thiết kế; gia hạn để người đang dùng không bị đá ra |
| **`get_current_user`** nạp `User` từ DB, kiểm `status` và `session_invalid_before` mỗi request | **Chép, bỏ** nhánh header `X-User-Id` | Bắt buộc: yêu cầu chỉ có `X-User-Id` phải bị từ chối (cổng của Phase 4) |
| **Logout chỉ xóa cookie** | **Đổi**: xóa cookie **và** thu hồi bằng `session_invalid_before` (quyết định D3) | Cổng của master-plan: "đăng xuất làm cookie cũ bị từ chối ngay" |
| `must_change_password`, `/change-password`, tùy chọn giọng điệu chat, membership dự án, `/select-project`, `describe_current_user` kèm dự án | **Bỏ** | Không có trong PRD chuẩn hoặc không có khái niệm dự án |
| Frontend: `useSession` (gọi `/me`, gia hạn định kỳ), chuyển `/login?next=` khi 401 | **Chép ý tưởng, viết lại theo Next 16** (bộ chặn ở phía server, không nhấp nháy) | Xem 4-B |
| `localStorage["ralion-demo-user-id"]` | **Bỏ** | Cơ chế dev không an toàn |

## 3. Quyết định cần bạn chốt (mặc định in đậm)

| # | Quyết định | Mặc định đề xuất | Lựa chọn khác |
|---|---|---|---|
| D1 | Tên vai trò và trang đích | Vai trò **`USER` = "Nhân sự mới"**, đích sau đăng nhập `/vi/chat`; `HR`, `ADMIN` đích `/vi/admin` | Gọi là "Kỹ sư mới" (giống Ralion) trong giao diện |
| D2 | Thời hạn phiên | **30 phút, tự gia hạn khi đang hoạt động** (`/auth/refresh`) | 8 giờ không gia hạn (đơn giản hơn, thu hồi chậm hơn) |
| D3 | Đăng xuất | **Xóa cookie và thu hồi mọi phiên của người dùng** (`session_invalid_before = now`); phiên ở thiết bị khác cũng mất | Chỉ xóa cookie (như Ralion, token bị lộ vẫn sống tới hết hạn) |
| D4 | Giới hạn thử sai | **5 lần sai trong 15 phút theo (email + IP) thì trả `429`**, đếm trong tiến trình (đủ cho một worker, ghi rõ giả định) | Đếm trong DB (cần bảng mới) |
| D5 | Tài khoản dev | **CLI nạp từ `registry/users.json`** (mật khẩu dev, băm khi nạp), **từ chối chạy khi `APP_ENV=production`**; production từ chối khởi động nếu còn tài khoản `@vsf-demo.example` | Nạp tự động lúc khởi động (dễ nhầm khi triển khai) |
| D6 | Bộ chặn trang | **`proxy.ts` chuyển về `/vi/login?next=` khi không có cookie; trang bảo vệ gọi `/auth/me` ở phía server**, sai chữ ký hoặc hết hạn thì chuyển hướng | Chỉ kiểm ở client (nhấp nháy nội dung) |
| D7 | Đổi mật khẩu bắt buộc | **Không làm ở MVP** | Làm như Ralion (thêm 0,5 ngày) |
| D8 | Trang cho HR/Admin | **Trang giữ chỗ** `/vi/admin` (tên, vai trò, đăng xuất) | Bỏ hẳn, chỉ có trang nhân sự mới |
| D9 | Cách kiểm | **pytest, Vitest, chụp ảnh và thử tay**; Playwright dời sang Phase 9 | Cài Playwright ngay (+0,3 ngày) |

## 4. Kế hoạch theo bước (mỗi bước một commit, có test)

| Bước | Nội dung | Ước lượng | Checkpoint |
|---|---|---|---|
| **4-A** | Backend xác thực | ≈ 0,6 ngày | **CP-4A**: bạn thử bằng `curl` (đăng nhập, `/me`, đăng xuất, cookie cũ bị từ chối) |
| **4-B** | Nối frontend: bộ chặn trang, đăng nhập thật, đăng xuất | ≈ 0,3 ngày | **CP-4B**: bạn đăng nhập và đăng xuất trên trình duyệt |
| **4-C** | Trang cho nhân sự mới (vỏ) và trang giữ chỗ HR/Admin | ≈ 0,4 ngày | **CP-4C**: bạn xem trang sau đăng nhập |
| **4-D** | Báo cáo, cập nhật tài liệu | ≈ 0,1 ngày | |
| Cộng | | **≈ 1,4 ngày** | Master-plan ước lượng 1,5 ngày; phần giao diện đăng nhập đã làm trước ở Phase 2 |

### 4-A. Backend xác thực (≈ 0,6 ngày)

**Tệp** (tên thư mục theo system design mục 3.1):

```text
backend/src/config.py                       + session_secret (SecretStr), session_ttl_seconds, validator production
backend/src/services/auth/passwords.py      hash_password, verify_password (scrypt)
backend/src/services/auth/sessions.py       issue_token, read_token, revocation_stamp, is_revoked, should_refresh, cookie_params
backend/src/services/auth/login_throttle.py giới hạn thử sai trong tiến trình (D4)
backend/src/services/auth/auth_service.py   login, logout (thu hồi), current_user_profile
backend/src/api/dependencies.py             get_current_user (cookie), require_role(*roles)
backend/src/api/routers/auth_router.py      POST /auth/login, POST /auth/logout, GET /auth/me, POST /auth/refresh
backend/src/dto/auth.py                     LoginRequest, SessionUser (khớp frontend), ErrorBody {code, message_key, detail}
backend/src/cli/seed_users.py               nạp teams và users từ registry/*.json (D5)
```

**Việc cụ thể.**
1. **Cấu hình:** `SESSION_SECRET` (bắt buộc ở production, ≥ 32 ký tự và không phải giá trị mẫu; validator từ chối khởi động), `SESSION_TTL_SECONDS` (mặc định 1800), cookie `vsf_session` với `httponly`, `samesite=lax`, `secure` khi `APP_ENV=production`, `path=/`.
2. **Đăng nhập:** chuẩn hóa email (chữ thường), so khớp mật khẩu bằng `verify_password` **kể cả khi không có người dùng** (băm giả để thời gian gần như nhau, tránh dò email); sai thì `401 INVALID_CREDENTIALS` (cùng một thông báo cho email lạ và mật khẩu sai); tài khoản `INACTIVE` thì `403 ACCOUNT_INACTIVE`; quá giới hạn thì `429 TOO_MANY_ATTEMPTS` kèm `Retry-After`; thành công thì cập nhật `last_login_at`, đặt cookie, trả `{id, email, display_name, role, expires_at}`.
3. **`get_current_user`:** đọc cookie, kiểm chữ ký và hạn, nạp `User` từ DB, từ chối nếu `INACTIVE` hoặc `issued_at < session_invalid_before`; **không** có nhánh nào đọc `X-User-Id`.
4. **`/auth/me`:** trả hồ sơ; chưa đăng nhập `401` (cổng smoke test công khai của deployment-ci). **`/auth/refresh`:** cấp cookie mới khi phiên đã dùng quá nửa TTL.
5. **`/auth/logout`:** xóa cookie **và** đặt `session_invalid_before = revocation_stamp()` (D3); gọi lại khi đã đăng xuất vẫn trả `204` (idempotent).
6. **`require_role`** cho `HR`, `ADMIN` (dùng ở phase sau); phản hồi `403 FORBIDDEN_ROLE`.
7. **Nạp dữ liệu dev:** `python -m src.cli.seed_users` đọc `registry/teams.json`, `registry/users.json` (9 người), băm `password_dev_only`, tạo `teams`, `users`, `team_members`; chạy lại không nhân đôi; từ chối khi `APP_ENV=production`.
8. **Khóa endpoint tạm của Phase 2** (`/api/v1/chat/ask`, khi có) sau `get_current_user`.
9. **Tài liệu API:** thêm `POST /auth/refresh` vào bảng ở system design mục 9; ghi lại giả định "giới hạn thử sai trong tiến trình".

**Test** (pytest, Postgres thật ở phần tích hợp):
- Đơn vị: băm và kiểm mật khẩu (đúng, sai, chuỗi lỗi định dạng); token (đúng, sửa một ký tự, sửa chữ ký, hết hạn, thiếu, sai định dạng); `revocation_stamp` không giết token phát hành **cùng giây** (lỗi đã gặp ở Ralion); giới hạn thử sai (đúng ngưỡng, hết cửa sổ, tách theo email/IP).
- Tích hợp: đăng nhập đúng đặt cookie `HttpOnly`; đăng nhập sai, email lạ, tài khoản bị khóa; `/me` với cookie hợp lệ, không cookie, cookie sai chữ ký, hết hạn; **đăng xuất rồi dùng lại cookie cũ bị `401`**; đăng nhập lại sau đăng xuất thành công (không bị đá); `refresh` chỉ gia hạn khi quá nửa TTL; **yêu cầu chỉ có `X-User-Id` bị `401`**; `require_role` trả `403` đúng vai trò; production từ chối khởi động với `SESSION_SECRET` yếu.
- Nạp tài khoản dev chạy hai lần không nhân đôi; từ chối ở production.

**Cổng.** `ruff`, `mypy`, `pytest` xanh; `alembic check` sạch (không thêm migration); CI xanh.

**CP-4A (bạn xem):** chuỗi `curl` mẫu (tôi soạn sẵn): đăng nhập `hr1@vsf-demo.example`, gọi `/me`, đăng xuất, gọi lại `/me` bằng cookie cũ phải `401`.

### 4-B. Nối frontend (≈ 0,3 ngày)

**Tệp:**

```text
frontend/src/features/auth/session.ts        + me(), logout(), refresh(); mã lỗi khớp {code, message_key}
frontend/src/features/auth/server-session.ts getSessionUser(): gọi /api/v1/auth/me ở phía server, chuyển tiếp cookie
frontend/src/features/auth/useSession.ts     hook client: gia hạn định kỳ khi tab đang mở (D2), đăng xuất
frontend/src/proxy.ts                        chặn /vi/chat, /vi/admin khi không có cookie vsf_session (D6)
frontend/src/app/[locale]/login/page.tsx     đã đăng nhập thì chuyển thẳng tới trang theo vai trò
frontend/src/app/[locale]/(app)/layout.tsx   nhóm route được bảo vệ: gọi getSessionUser, 401 thì chuyển /vi/login?next=
```

**Việc cụ thể.**
1. `authApi.login` đã có (Phase 2); thêm `me`, `logout`, `refresh` với `credentials: "include"` và không header định danh tự chế.
2. **Bộ chặn hai lớp:** `proxy.ts` chỉ kiểm **có cookie** để chuyển hướng nhanh (không thể kiểm chữ ký nếu không có bí mật ở proxy); layout của nhóm `(app)` gọi `/auth/me` ở phía server, sai chữ ký, hết hạn hoặc bị thu hồi thì chuyển tới `/vi/login?next=<đường dẫn nội bộ đã kiểm>`. Trang bảo vệ trả `Cache-Control: no-store` để nút "Back" sau đăng xuất không hiện lại nội dung cũ.
3. **Chuyển trang theo vai trò** dùng hàm `resolvePostLoginPath` đã có test (USER tới `/chat`, HR/ADMIN tới `/admin`); người dùng `USER` mở `/vi/admin` thì chuyển về `/vi/chat`.
4. **Đăng nhập thật:** bỏ trạng thái "chưa nối API" ở form; lỗi `401/403/429` đã có thông báo (`invalid`, `unavailable`, `tooMany`); thêm thông báo khóa tài khoản (`ACCOUNT_INACTIVE`) vào `messages` (vi và en).
5. **Đăng xuất:** `authApi.logout()` rồi chuyển `/vi/login`; nếu gọi lỗi vẫn chuyển (cookie đã bị xóa phía server hoặc hết hạn).

**Test (Vitest):** `getSessionUser` (200, 401, lỗi mạng); bộ chặn (không cookie chuyển hướng giữ `?next=` nội bộ; có cookie đi tiếp; `/vi/login` không bị chặn; `/api`, `/_next` không bị chặn); trang đăng nhập khi đã đăng nhập; đăng xuất gọi API rồi chuyển trang kể cả khi API lỗi; `?next=` độc hại vẫn bị loại (đã có).

**Cổng.** `lint`, `typecheck`, `test`, `build` xanh.

**CP-4B (bạn xem):** trình duyệt: đăng nhập sai (thấy lỗi), đăng nhập đúng (tới trang đúng vai trò), bấm đăng xuất (về `/vi/login`), bấm Back (không thấy lại trang bảo vệ), mở `/vi/chat` khi chưa đăng nhập (bị chuyển kèm `?next=`).

### 4-C. Trang cho nhân sự mới (vỏ) và trang giữ chỗ HR/Admin (≈ 0,4 ngày)

Đây là **màn hình đầu tiên nhân sự mới thấy sau khi đăng nhập**. Bố cục tham khảo các trang trong app của Ralion (`features/chat/ChatScreen.tsx`) nhưng viết lại theo token và SCSS của VSF; chữ ở `messages/vi.json` và `en.json`.

**Tệp:**

```text
frontend/src/app/[locale]/(app)/chat/page.tsx       trang nhân sự mới
frontend/src/app/[locale]/(app)/admin/page.tsx      trang giữ chỗ cho HR/Admin
frontend/src/features/app-shell/AppHeader.tsx       logo, chọn ngôn ngữ, menu người dùng (tên, vai trò, Đăng xuất)
frontend/src/features/chat/ChatShell.tsx            lời chào, câu hỏi gợi ý, danh sách tin nhắn, ô nhập (dữ liệu giả)
frontend/src/features/chat/mockAnswer.ts            câu trả lời mẫu từ bộ seed (đánh dấu rõ là minh họa)
frontend/src/features/chat/chat.test.tsx
```

**Nội dung trang `/vi/chat`:**
1. **Header:** logo, chọn ngôn ngữ, **menu người dùng** (chữ cái đầu tên, tên hiển thị, vai trò, "Đăng xuất").
2. **Lời chào cá nhân:** "Chào {tên}, bạn cần biết điều gì?" và ghi chú "Trợ lý trả lời từ tài liệu đã được duyệt".
3. **Câu hỏi gợi ý** (bấm để điền vào ô nhập), lấy từ bộ câu hỏi dev đã dùng ở Phase 2: nghỉ phép năm, VPN, cài phần mềm, chỗ ngồi, đầu mối IT.
4. **Khung chat:** danh sách tin nhắn, ô nhập, nút gửi, trạng thái đang tải, lỗi, "chưa có căn cứ", khối **Nguồn** (trích dẫn, tên tài liệu, phiên bản). **Dữ liệu giả** (chế độ `mock`) và dòng nhắc "Bản minh họa, chưa nối máy chủ trả lời"; chuyển sang thật ở 2-E.
5. **Điện thoại:** một cột, ô nhập dính đáy.

**Trang `/vi/admin` (HR/Admin):** giữ chỗ, hiển thị tên, vai trò, "Khu quản lý sẽ có ở các phase sau" và nút đăng xuất; giúp kiểm điều hướng theo vai trò.

**Test:** người dùng `USER` thấy lời chào đúng tên và menu; bấm gợi ý điền vào ô nhập; gửi hiện câu trả lời mẫu kèm nguồn; lỗi hiển thị; menu có nút đăng xuất gọi API; `USER` mở `/admin` bị chuyển về `/chat`; HR mở `/admin` thấy trang giữ chỗ; quét mã nguồn không chữ Việt cứng, không mã màu hex ngoài SCSS.

**Cổng.** `lint`, `typecheck`, `test`, `build` xanh; ảnh chụp 1440 px và 375 px, cả hai ngôn ngữ; không tràn ngang.

**CP-4C (bạn xem):** đăng nhập bằng `hr1@vsf-demo.example` (thử `/admin`) và một tài khoản `USER` trong `registry/users.json` (thử `/chat`); tôi gửi ảnh chụp kèm.

### 4-D. Báo cáo và cập nhật tài liệu (≈ 0,1 ngày)

`plan/phase-4/bao-cao-phase-4.md` (kết quả, số đo, sai lệch, giờ công); cập nhật `master-plan.md` (Phase 4 xong, thứ tự), `plan/README.md`, system design mục 9 (thêm `/auth/refresh`, mô tả đăng xuất thu hồi), README gốc (cách nạp tài khoản dev và đăng nhập thử), `.env.example` (`SESSION_SECRET`, `SESSION_TTL_SECONDS`), `frontend-login-reuse.md` (trạng thái).

## 5. Cổng hoàn thành của Phase 4 (theo master-plan, có bổ sung)

| # | Điều kiện | Cách kiểm |
|---|---|---|
| 1 | pytest xanh; đăng xuất và thu hồi làm cookie cũ bị từ chối ngay | 4-A |
| 2 | Yêu cầu chỉ có `X-User-Id` bị từ chối; `grep` không thấy `X-User-Id`, `ralion-demo-user-id`, "Ralion" trong mã VSF | Test và `grep` |
| 3 | Đăng nhập tài khoản dev tới đúng trang theo vai trò; chưa đăng nhập không vào được trang bảo vệ | 4-B, kiểm tay và Vitest (Playwright dời sang Phase 9) |
| 4 | Production từ chối khởi động nếu `SESSION_SECRET` yếu hoặc còn tài khoản dev | Test cấu hình |
| 5 | Nhân sự mới sau đăng nhập thấy trang chào, gợi ý và chat (giả), có đăng xuất | 4-C |
| 6 | `lint`, `typecheck`, `test`, `build`, `ruff`, `mypy` xanh; CI xanh | |

## 6. Rủi ro và cách xử lý

| Rủi ro | Xử lý |
|---|---|
| **Mật khẩu dev lọt vào môi trường thật** | CLI từ chối ở production; production từ chối khởi động nếu còn tài khoản `@vsf-demo.example`; ghi vào danh sách kiểm trước deploy |
| **`SESSION_SECRET` yếu hoặc để mặc định** | Validator cấu hình bắt buộc ở production; `.env.example` chỉ có chỗ trống |
| **Cookie không gửi qua rewrite của Next ở dev** | Dev dùng rewrite `/api/*` cùng origin nên cookie là first-party; thử ngay ở CP-4A/4-B; production dùng Caddy cùng origin |
| **Lỗi "vừa đăng nhập lại vẫn bị đá ra"** (đã gặp ở Ralion) | `revocation_stamp` cắt giây, có test cùng giây |
| **Dò email qua thời gian phản hồi** | Băm giả khi không có người dùng, cùng một thông báo lỗi |
| **Giới hạn thử sai trong tiến trình mất khi khởi động lại, không chia sẻ giữa nhiều worker** | Ghi rõ giả định một worker (MVP); chuyển vào DB nếu chạy nhiều worker |
| **Thời gian băm scrypt làm chậm test** | Tham số như Ralion (`n=2^14`); test dùng ít tài khoản; nếu chậm, hạ `n` chỉ trong fixture kiểm thử |
| **Nhấp nháy nội dung bảo vệ hoặc "Back" sau đăng xuất** | Bộ chặn phía server, `Cache-Control: no-store`, chuyển hướng trước khi hiển thị |
| **Đảo thứ tự làm muộn số đo giờ công của Phase 2** | Ghi giờ công thật ở từng bước Phase 4; hiệu chỉnh lịch vẫn làm ở 2-F |
| **CSRF** | Cookie `SameSite=Lax`; mọi API ghi dùng `POST/PATCH` với `Content-Type: application/json` (form chéo trang không gửi được loại này) |

## 7. Thứ tự tiếp theo sau Phase 4

1. **Quay lại lõi:** 2-B (nạp tài liệu), 2-C (tìm kiếm hybrid, mở đầu bằng thử BM25), 2-D (LLM và validator).
2. **2-E nối trang chat của 4-C với endpoint thật** `POST /api/v1/chat/ask` (đã sau đăng nhập); U3 của kế hoạch Phase 2 được gộp vào 4-C.
3. Khi có khóa DeepSeek và Modal: chạy bộ 10 câu, đo, viết báo cáo (2-F).

## 8. Điều tôi cần từ bạn

- Chốt D1 đến D9 (hoặc "dùng mặc định").
- Xác nhận **đổi thứ tự**: Phase 4 trước, rồi lõi Phase 2 (2-B đến 2-F).
- Vẫn còn treo từ CP-2A: khóa ngoại `team_members` `RESTRICT` hay `CASCADE` (ảnh hưởng `seed_users`).
