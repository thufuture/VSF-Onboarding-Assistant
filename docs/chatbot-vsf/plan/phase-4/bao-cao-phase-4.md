# Báo cáo Phase 4 — tiến độ và các checkpoint (cập nhật 21/09/2026)

> Kế hoạch: [phase-4.md](phase-4.md). Nhánh `phase-4-auth` (từ `phase-2-vertical-slice`). **Đã commit cục bộ, chưa push, chưa mở PR.**
> Đã dùng mặc định cho D1 đến D9 và thứ tự "Phase 4 trước, rồi lõi Phase 2". `team_members` vẫn để `RESTRICT` (bạn chưa chọn `CASCADE`).
> **Kết luận: 4-A (backend xác thực) đã xong và kiểm chứng trên PostgreSQL thật. DTO đã tách `request`/`response` ở cả backend và frontend theo cách của Ralion. 4-B (nối frontend) và 4-C (trang nhân sự mới) chưa làm. Đang chờ bạn xem CP-4A.**

## 1. Checkpoint

| Checkpoint | Nội dung | Trạng thái |
|---|---|---|
| **CP-4A** | Backend xác thực: bạn thử bằng `curl` (mục 4) | **Sẵn sàng để xem** |
| CP-4B | Đăng nhập, đăng xuất trên trình duyệt | Chưa làm |
| CP-4C | Trang nhân sự mới sau đăng nhập | Chưa làm |

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

## 7. Bước tiếp theo

**4-B** nối frontend: `me`, `logout`, `refresh`, bộ chặn trang, đăng nhập thật; rồi **4-C** trang nhân sự mới (theo [phase-4.md](phase-4.md) mục 4).
