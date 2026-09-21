# Báo cáo Phase 4 — tiến độ và các checkpoint (cập nhật 21/09/2026)

> Kế hoạch: [phase-4.md](phase-4.md). Nhánh `phase-4-auth` (từ `phase-2-vertical-slice`). **Đã commit cục bộ, chưa push, chưa mở PR.**
> Đã dùng mặc định cho D1 đến D9 và thứ tự "Phase 4 trước, rồi lõi Phase 2". `team_members` vẫn để `RESTRICT` (bạn chưa chọn `CASCADE`).
> **Kết luận: 4-A (backend xác thực) đã xong và kiểm chứng trên PostgreSQL thật. DTO đã tách `request`/`response` ở cả backend và frontend theo cách của Ralion. 4-B (nối frontend: chặn trang, đăng nhập, đăng xuất thật) và 4-C (trang nhân sự mới, trang giữ chỗ HR/Admin) cũng đã xong và kiểm chứng trên trình duyệt thật. 4-D (cập nhật tài liệu tổng) cũng đã xong.**

## 1. Checkpoint

| Checkpoint | Nội dung | Trạng thái |
|---|---|---|
| **CP-4A** | Backend xác thực: bạn thử bằng `curl` (mục 4) | **Xong** |
| CP-4B | Đăng nhập, đăng xuất trên trình duyệt | **Xong**, xem mục 8 |
| CP-4C | Trang nhân sự mới sau đăng nhập | **Xong**, xem mục 8 và [screenshots/](screenshots/) |

## 2. Đã làm ở 4-A

| Nhóm | Nội dung |
|---|---|
| Cấu hình (`config.py`) | `SESSION_SECRET` (bắt buộc và phải mạnh ở production: ≥ 32 ký tự, không chứa "change/secret/password/example/default/dev", đủ đa dạng ký tự; ngoài production để trống thì tự sinh khóa ngẫu nhiên), `SESSION_TTL_SECONDS` (1800), `LOGIN_MAX_FAILURES` (5), `LOGIN_WINDOW_SECONDS` (900) |
| Mật khẩu (`services/auth/passwords.py`) | scrypt (`n=2^14, r=8, p=1`) như Ralion; băm giả khi email không tồn tại để thời gian phản hồi gần như nhau |
| Phiên (`services/auth/sessions.py`) | Cookie `vsf_session` ký HMAC-SHA256, dạng `uid.iat_ms.exp.chữ_ký`; kiểm chữ ký bằng `compare_digest` **trước** khi tin trường nào; thu hồi bằng `users.session_invalid_before`; gia hạn khi đã quá nửa thời hạn |
| Giới hạn thử sai (`login_throttle.py`) | 5 lần sai trong 15 phút theo (email, IP) thì `429` kèm `Retry-After`; đếm trong tiến trình, bộ nhớ có trần; đăng nhập đúng xóa bộ đếm |
| Dịch vụ (`auth_service.py`) | `authenticate` (kiểm giới hạn trước khi băm; cùng thông báo cho email lạ và mật khẩu sai; tài khoản khóa chỉ lộ khi mật khẩu đúng), `start_session`, `load_session_user` (từ chối người dùng bị khóa hoặc phiên bị thu hồi), `revoke_sessions` |
| API (`/api/v1/auth`) | `POST /login`, `GET /me`, `POST /refresh`, `POST /logout` (`204`, xóa cookie **và** thu hồi mọi phiên); lỗi một hình dạng `{code, message_key, detail}` |
| Phụ thuộc (`api/dependencies.py`) | `get_current_session`, `get_current_user` (**chỉ** cookie, không có nhánh header nào), `require_role(*roles)` (`403 FORBIDDEN_ROLE`) |
| Tài khoản dev | `python -m src.cli.seed_users` nạp `registry/teams.json` và `users.json` (4 đội, 9 người, 5 thành viên đội); chạy lại không nhân đôi; **từ chối ở production**; production cũng từ chối khởi động nếu còn tài khoản `@vsf-demo.example` |
| **DTO tách request/response** | Backend: `dto/request/auth_request_dto.py` (`LoginRequestDTO`), `dto/response/{auth,error,health}_response_dto.py` (`SessionUserResponseDTO`, `ErrorResponseDTO`, `HealthResponseDTO`, `ReadyResponseDTO`). Frontend: `features/auth/dto/requestDTO/auth.request.ts`, `features/auth/dto/responseDTO/auth.response.ts`, kiểu lỗi dùng chung `types/apiError.ts`. Có test giữ quy ước tên tệp và tên kiểu ở cả hai phía |

## 3. Kiểm chứng

| Kiểm | Kết quả |
|---|---|
| Backend: `ruff`, `ruff format --check`, `mypy` (strict) | Sạch |
| Backend: `pytest` (PostgreSQL/ParadeDB thật) | **95 qua** (trước Phase 4 có 36): thêm test đơn vị cho mật khẩu, token, thu hồi, giới hạn thử sai và cấu hình; 19 test tích hợp API xác thực; 4 test quy ước DTO |
| `alembic check` | Sạch (Phase 4 không thêm migration) |
| Frontend: `lint`, `typecheck`, `test`, `build` | Xanh, **100 test** (thêm test 403 khóa tài khoản và bố cục `dto`) |
| Chạy thật bằng `curl` trên backend thật | Xem mục 4 |

Các ca đã có test: đăng nhập đúng đặt cookie `HttpOnly; SameSite=lax; Path=/` (không `Secure` ở dev); email không phân biệt hoa thường; sai mật khẩu và email lạ **không phân biệt được**; tài khoản khóa chỉ lộ khi mật khẩu đúng; giới hạn thử sai theo IP và được xóa khi đăng nhập đúng; cookie bị sửa, hết hạn, mượn chữ ký của người khác đều `401`; **`X-User-Id` không có tác dụng**; **đăng xuất thu hồi cookie cũ ngay** và mọi thiết bị khác của cùng người dùng; **đăng nhập lại ngay sau đăng xuất luôn thành công** (lỗi từng gặp ở Ralion); khóa tài khoản hoặc thu hồi trực tiếp trong DB làm phiên đang mở bị từ chối; `refresh` chỉ gia hạn phiên đã dùng quá nửa; phân quyền `403`; nạp tài khoản dev không nhân đôi.

## 4. CP-4A: chuỗi `curl` bạn có thể tự chạy

Trong `backend/`: `python -m src.cli.seed_users` (một lần), rồi `python -m uvicorn src.main:app --port 8100`. Kết quả đã chạy thật:

```text
1. GET  /me chưa đăng nhập         -> 401 {"code":"UNAUTHENTICATED","message_key":"auth.unauthenticated","detail":null}
2. POST /login sai mật khẩu        -> 401 {"code":"INVALID_CREDENTIALS",...}
3. POST /login hr1@vsf-demo.example / ChangeMe!123
                                   -> 200, set-cookie: vsf_session=<token>; HttpOnly; Max-Age=1800; Path=/; SameSite=lax
                                      {"id":75,"email":"hr1@vsf-demo.example","display_name":"HR Demo 1","role":"HR","expires_at":"..."}
4. GET  /me kèm cookie             -> 200 (hồ sơ như trên)
5. POST /logout                    -> 204
6. GET  /me bằng cookie CŨ         -> 401 {"code":"SESSION_REVOKED",...}
7. GET  /me chỉ có X-User-Id: 1    -> 401 UNAUTHENTICATED
8. POST /login ngay sau đăng xuất  -> 200, /me -> 200
```

## 5. Sai lệch so với kế hoạch

| # | Nội dung | Vì sao |
|---|---|---|
| 1 | Token lưu **thời điểm phát hành bằng mili giây** (`uid.iat_ms.exp.sig`), mốc thu hồi chính xác tới mili giây; đăng xuất đặt mốc `now + 1 ms` | Ralion cắt xuống giây nên token cấp cùng giây với lúc thu hồi vẫn sống (đăng xuất xong dùng lại cookie cũ trong cùng giây vẫn qua). Cách này để token cũ luôn chết và token cấp sau đăng nhập lại luôn sống (`next_issue_ms`) |
| 2 | Ngoài production, để trống `SESSION_SECRET` thì tự sinh khóa | Tiện cho dev và test; production vẫn bắt buộc khóa mạnh và từ chối khởi động nếu yếu |
| 3 | Thêm DTO `HealthResponseDTO`, `ReadyResponseDTO` cho `/health`, `/ready` | Câu hỏi mở từ Phase 1 ("thêm `dto/` với health DTO"); trả lời theo yêu cầu tách DTO |
| 4 | Đăng nhập `403` ở frontend được tách thành "tài khoản bị khóa" (`account_inactive`) thay vì gộp với sai mật khẩu | Backend trả `ACCOUNT_INACTIVE` riêng; thêm thông báo tiếng Việt và tiếng Anh |
| 5 | Test gia hạn dùng `client.cookies.set` thay vì tham số cookie theo từng request | httpx đã đánh dấu cách cũ là bị loại bỏ |

## 6. Việc theo dõi (không chặn)

- **Giả định một worker** cho bộ đếm đăng nhập sai (ghi trong mã và plan); chuyển vào DB nếu chạy nhiều worker.
- **IP của client** lấy từ `request.client.host`; sau Caddy cần cho uvicorn tin `X-Forwarded-For` (`--proxy-headers`, chỉ tin Caddy) ở Phase 11a, nếu không mọi người dùng cùng một IP (127.0.0.1 hoặc IP Docker) và bộ đếm chung cho cả nhóm.
- Compose cục bộ vẫn dùng ảnh backend cũ chưa có `/auth/*`: cần `docker compose up -d --build backend` để thử qua cổng 8000.

## 7. 4-B và 4-C: nối frontend và trang sau đăng nhập

| Nhóm | Nội dung |
|---|---|
| Gọi API (`features/auth/session.ts`) | Thêm `me()`, `refresh()` (trả `null` khi 401) và `logout()` (báo lỗi khi backend lỗi hoặc mất mạng, để giao diện không giả vờ đã đăng xuất) |
| Bộ chặn trang (`proxy.ts`) | `/vi/chat`, `/vi/admin` (và `/en/...`) **không có cookie `vsf_session`** thì chuyển về `/<ngôn ngữ>/login?next=<đường dẫn>`; trang bảo vệ có `Cache-Control: no-store` |
| Kiểm cookie thật (`features/auth/server.ts`, `app/[locale]/(app)/layout.tsx`) | Layout của khu bảo vệ gọi `/auth/me` ở phía server bằng cookie của trình duyệt: cookie giả, hết hạn hoặc bị thu hồi thì chuyển về đăng nhập (không nhấp nháy nội dung) |
| Đã đăng nhập mà mở trang đăng nhập (`login/layout.tsx`) | Chuyển tới trang mặc định của vai trò |
| Vai trò | `USER` mở `/admin` bị chuyển về `/chat`; `HR` và `ADMIN` vào `/admin` |
| Phiên phía client (`SessionProvider`, `useSession`) | Gia hạn mỗi 5 phút khi tab mở; phiên mất hiệu lực thì chuyển về đăng nhập; lỗi mạng tạm thời giữ nguyên |
| Đăng xuất (`AppHeader`) | Gọi `/auth/logout` rồi về `/login`; lỗi thì ở lại và hiện thông báo |
| Trang nhân sự mới (`features/chat/ChatShell`) | Lời chào theo tên, ghi chú "nội dung minh họa", 4 câu hỏi gợi ý cho câu trả lời kèm khối **Nguồn**, câu hỏi tự gõ nhận "chưa có tài liệu đã duyệt" (không bịa) |
| Trang giữ chỗ HR/Admin (`features/app-shell/AdminPlaceholder`) | Lời chào, vai trò, danh sách việc sắp có, đường về chat |
| Giao diện | SCSS module, cùng token màu, phông và logo với landing; điện thoại (375 px) thu nút đăng xuất thành biểu tượng để đủ chỗ; song ngữ vi/en |

**Thiết kế lại giao diện nhân sự mới (theo bố cục portal và chat của Ralion):** khung `AppShell` gồm thanh bên (logo hai dòng "VSF Onboarding" xanh / "Assistant" đen, điều hướng theo vai trò, mục chưa có trang mờ kèm nhãn "Sắp có", thẻ người dùng, đăng xuất) và thanh trên (chọn ngôn ngữ, sáng/tối). Chat: màn chào với 4 thẻ gợi ý, câu hỏi bên phải, trả lời bên trái có avatar, chấm "đang tìm nguồn", chip nguồn bấm mở trích đoạn, ô nhập tự cao (Enter gửi, Shift+Enter xuống dòng), nút cuộc trò chuyện mới, chế độ tối (nhớ lựa chọn), điện thoại dùng ngăn kéo. Vẫn là dữ liệu minh họa. Tiêu đề trang, nhãn phạm vi, chọn ngôn ngữ và sáng/tối nằm chung một thanh trên; dưới tên người dùng hiện **phòng ban** (`department` mới trong `/auth/me`, `/auth/login`, `/auth/refresh`, lấy từ `team_members`; nhiều đội nối bằng ", "). Tài khoản chưa thuộc đội nào (admin, newhire1 đến 3 trong dữ liệu dev) hiện vai trò thay thế, vì mô hình dữ liệu chưa có phòng ban cho nhân sự mới.

Kiểm chứng: `lint`, `typecheck`, `build` xanh; **137 test frontend** (trước khi thiết kế lại: 128) và **96 test backend** (thêm test phòng ban) (thêm 28: cổng đăng nhập ở proxy, `me/refresh/logout`, đầu trang, `SessionProvider`, chat, trang giữ chỗ).

Chạy thật trên trình duyệt (Chrome headless qua CDP, backend thật, tài khoản dev):

```text
/vi/chat không cookie              -> 307 /vi/login?next=%2Fvi%2Fchat
/vi/chat cookie giả                -> 307 /vi/login
đăng nhập it.staff (USER)          -> 200; /vi/chat 200 ("Xin chào, IT Staff Demo")
/vi/admin với USER                 -> 307 /vi/chat
/vi/login khi đã đăng nhập         -> 307 /vi/chat  (HR: 307 /vi/admin)
bấm câu hỏi gợi ý                  -> hiện câu trả lời kèm "Nguồn: ... (minh họa)"
bấm Đăng xuất                      -> /vi/login; mở lại /vi/chat -> /vi/login
```

Ảnh: [chat 1440 vi](screenshots/chat-1440-vi.png), [chế độ tối](screenshots/chat-1440-vi-toi.png), [ngăn kéo điện thoại](screenshots/chat-375-menu.png), [chat sau khi hỏi](screenshots/chat-1440-vi-hoi.png), [chat 375](screenshots/chat-375-vi.png), [chat 1440 en](screenshots/chat-1440-en.png), [admin](screenshots/admin-1440-vi.png), [chưa đăng nhập bị chuyển](screenshots/chat-chua-dang-nhap.png).

Lưu ý khi tự thử: trong chế độ dev, Next chặn tài nguyên khi mở bằng `127.0.0.1` (trang không tương tác được); hãy mở bằng **`http://localhost:3000`**. Frontend dev gọi backend qua `API_UPSTREAM_URL` (mặc định cổng 8000, là ảnh Docker cũ chưa có `/auth/*`): chạy `API_UPSTREAM_URL=http://127.0.0.1:8100 npm run dev` với backend `uvicorn --port 8100`, hoặc build lại ảnh backend.

## 8. Việc chưa làm ở Phase 4

- Chưa kiểm tra chế độ tối và Lighthouse; Playwright dời sang Phase 9.
- Chưa push và chưa mở PR cho `phase-4-auth`.

## 9. Bước tiếp theo

**Phase 4 xong.** Quay lại lõi Phase 2 (2-B nạp tài liệu, 2-C tìm kiếm, 2-D LLM, 2-E nối chat thật vào trang `/vi/chat`).
