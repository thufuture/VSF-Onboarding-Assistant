# Tái sử dụng giao diện đăng nhập của Ralion

> Trạng thái: **bản nháp v4 để duyệt**. Thuộc [master-plan.md](master-plan.md), **Phase 4** [Bắt buộc] (giao diện và nối API làm cùng một phase, ≈ 1,5 ngày công gồm cả xác thực phía backend; bảng `users`/`teams`/`team_members` đã có từ `0001_core` nên không có migration ở phase này, và không có bảng `sessions`). Landing page làm sau (Phase 10) nên trang login **không** dùng Navbar của landing.
> Nguồn: mã Ralion trong repo `P-040` (đã đọc), gồm `frontend/src/app/login/page.tsx`, `page.module.css`, `page.test.tsx`, `features/auth/routing.ts`, `features/auth/session.ts`, và khối `login` trong `messages/vi.json`.
> **MVP chỉ có tiếng Việt**: không chép `LanguageSwitcher`, không làm bản `en`; chỉ giữ cấu trúc `messages/vi.json` để thêm `en` sau.

## 1. Quyết định

Chép có chọn lọc trang đăng nhập của Ralion sang repo mới rồi chỉnh cho VSF: **giữ bố cục và các thành phần giao diện đã kiểm chứng, đổi thương hiệu và chữ, bỏ mọi thứ đặc thù của Ralion hoặc kém an toàn.** Không phụ thuộc vào repo Ralion sau khi chép.

Cần lưu ý ảnh chụp cũ trong `frontend/output/playwright/login-desktop.png` là **thiết kế cũ** (nền phong cảnh xanh lá, chữ "Ralion"). Mã hiện tại là bố cục hai cột xanh dương. Tái sử dụng theo **mã hiện tại**, không theo ảnh chụp.

## 2. Giữ lại (chép rồi chỉnh)

| Phần | Ở đâu trong Ralion | Ghi chú cho VSF |
|---|---|---|
| Bố cục hai cột: panel bên trái (gradient, viền cắt hình mũi tên) + thẻ form bên phải | `page.module.css` (`.loginMain`, `.storyPanel`, `.card`) | Giữ; ≤ 980px xếp một cột, ≤ 680px ẩn panel trái |
| Ô nhập có biểu tượng, trạng thái focus/hover/disabled | `.inputControl`, `.input` | Giữ; biểu tượng lấy từ `@primer/octicons-react` như Ralion |
| Nút gửi có spinner, hộp lỗi `role="alert"` | `.submit`, `.spinner`, `.error` | Giữ |
| Đọc giá trị từ `FormData` để trình quản lý mật khẩu điền tự động vẫn hoạt động; `autoComplete="username"` / `"current-password"` | `submit()` trong `page.tsx` | Giữ nguyên cách làm |
| Kiểm email phía client | `submit()` | Giữ |
| Chuyển động `reveal` và `prefers-reduced-motion` | cuối `page.module.css` | Giữ |
| Chặn chuyển hướng ra ngoài sau đăng nhập (chỉ nhận đường dẫn nội bộ, loại `//`), tham số `?next=` | `internalPath()` trong `features/auth/routing.ts` | Giữ và **thêm test** cho các giá trị như `//evil.com`, `/\evil.com`, `https://evil.com`, `javascript:` |
| Cấu trúc test của trang | `page.test.tsx` | Dùng làm khung, sửa cho khớp |
| Cách gọi API: `fetch` với `credentials: "include"`, lớp lỗi `SessionError` | `features/auth/session.ts` | Giữ dạng; đổi endpoint sang `/api/v1/auth/*` |

## 3. Đổi

| Ralion | VSF |
|---|---|
| Thương hiệu `RalionBrand` | Chữ "VSF Onboarding Assistant" + nhãn "Bản demo thực tập" (không dùng logo Vin/VSF khi chưa được đồng ý, xem [landing-page-plan.md](landing-page-plan.md) mục 5) |
| Nhiều mã màu hex viết cứng trong CSS, biến `--ralion-*` | Dùng token thiết kế của Phase 1 (`--vsf-*`); login và landing cùng một bộ token để nhìn thống nhất |
| Chữ vi/en viết cứng trong component (`copy = locale === "vi" ? {…} : {…}`), trùng lặp với `messages/*.json` | Toàn bộ chữ nằm trong `messages/vi.json`, khối `login`; không còn chuỗi trong component, không còn nhánh theo `locale` |
| Thanh điều hướng riêng của trang login (ba liên kết trỏ về landing, công tắc ngôn ngữ) | Header chỉ có thương hiệu (chưa có landing để trỏ về); khi Phase 10 xong có thể nối lại |
| Panel trái: "Onboarding thông minh theo dự án", ba lợi ích về codebase/dự án | Nội dung VSF: ba nguyên tắc (có nguồn dẫn chứng, không đoán dữ liệu cá nhân, chỉ dùng link đã duyệt); văn bản chốt cùng bạn |
| `resolvePostLoginPath` theo `ADMIN`/`HR`/thành viên dự án, đích `/select-project` | Theo vai trò của VSF: nhân viên → trang chat; HR/Owner/Admin → khu quản trị (tên route theo [system design mục 11](../vsf-onboarding-assistant-system-design.md)); vẫn chỉ chấp nhận `?next=` nếu hợp lệ với vai trò |
| Kiểm `minLength = 8` ở client và thông báo "ít nhất 8 ký tự" | Chỉ yêu cầu không rỗng ở trang đăng nhập; chính sách độ dài mật khẩu do server quyết định khi đặt mật khẩu (tránh trùng lặp chính sách và chặn nhầm mật khẩu hợp lệ) |
| Hai route login: `app/login` và `app/[locale]/login` (cái sau chỉ re-export cái trước) | Chỉ giữ `app/[locale]/login` |

## 4. Bỏ

| Phần của Ralion | Lý do |
|---|---|
| Nút và cửa sổ xem video demo, `iframe` Google Drive | Chưa có video VSF; không nhúng khung bên thứ ba vào trang đăng nhập |
| `LanguageSwitcher` và toàn bộ bản `en` | MVP chỉ tiếng Việt (quyết định đã chốt); thêm sau MVP |
| Khối "tài khoản test" trỏ tới Google Doc của Ralion (`TEST_ACCOUNT_GUIDE_URL`) | Là liên kết ngoài cứng trong mã và trỏ tới tài liệu Ralion. Nếu cần gợi ý tài khoản dev, chỉ hiện ở bản demo, lấy từ `registry/users.json` |
| `localStorage["ralion-demo-user-id"]` và header `X-User-Id` (`authHeaders()` trong `session.ts`) | Là cơ chế dev cho phép gửi định danh người dùng qua header. **Không đưa vào VSF**; phiên chỉ dựa vào cookie ký HMAC. Backend mới không được nhận header này |
| Nhánh `MUST_CHANGE_PASSWORD`, `NO_ACTIVE_PROJECT`, `/select-project`, `/change-password` | Đặc thù mô hình theo dự án của Ralion. VSF không có dự án. Đổi mật khẩu bắt buộc chưa có trong PRD chuẩn; nếu tài khoản HR cấp cần mật khẩu tạm thì thêm sau (câu hỏi mở) |
| "Quên mật khẩu", "Tạo tài khoản" (ở thiết kế cũ) | Tài khoản do HR/Admin tạo, không có tự đăng ký trong MVP |

## 5. Việc cần làm (tất cả thuộc Phase 4)

| # | Việc | Ước lượng |
|---|---|---|
| R1 | Chép `page.tsx`, `page.module.css`, `page.test.tsx` vào `app/[locale]/login` (không chép `LanguageSwitcher`) | 0,15 ngày |
| R2 | Đổi thương hiệu, thay hex bằng token, đưa chữ ra `messages/vi.json`, header chỉ có thương hiệu, bỏ video/khối tài khoản test | 0,35 ngày |
| R3 | Nối `authApi.login` / `me` với `/api/v1/auth/*`; `resolvePostLoginPath` theo vai trò VSF; **không** chép `authHeaders()`/`X-User-Id` | 0,25 ngày |
| R4 | Test: email hợp lệ/không hợp lệ, lỗi từ server hiện đúng, `?next=` an toàn (các giá trị độc hại ở mục 2), chuyển đúng trang theo vai trò | 0,25 ngày |

Phần giao diện ≈ 1 ngày công; phần backend xác thực (cookie HMAC, `session_invalid_before`, vai trò) nằm trong 1,5 ngày của Phase 4 ở [master-plan.md](master-plan.md).

## 6. Cổng hoàn thành

- Vitest: email sai → thông báo lỗi; mật khẩu rỗng bị chặn; giá trị `?next=` độc hại đều rơi về trang mặc định theo vai trò.
- Playwright: mở `/vi/login`, chụp ảnh 375 và 1280 px, không tràn ngang; đăng nhập bằng tài khoản dev từ `registry/users.json` và tới đúng trang theo vai trò.
- Kiểm tay: trang không còn chữ "Ralion", không còn liên kết Google Drive/Docs; `grep` không thấy `X-User-Id`, `ralion-demo-user-id`, `LanguageSwitcher` trong mã VSF.
- Backend: yêu cầu có header `X-User-Id` mà không có cookie hợp lệ phải bị từ chối.

## 7. Rủi ro

| Rủi ro | Xử lý |
|---|---|
| Chép luôn cả hành vi kém an toàn (`X-User-Id`) | Danh sách "Bỏ" ở trên làm mốc; cổng kiểm `grep` và test backend |
| Trang login và landing (làm sau, Phase 10) lệch phong cách | Cùng token thiết kế; rà lại khi làm landing |
| CSS chép về còn màu Ralion | Test quét mã tìm hex cứng và `--ralion-` trong `features/`/`app/` |
| Nhân đôi chữ giữa component và tệp dịch như bản Ralion | Quy tắc "không chuỗi giao diện trong component" kiểm bằng eslint/Vitest |
