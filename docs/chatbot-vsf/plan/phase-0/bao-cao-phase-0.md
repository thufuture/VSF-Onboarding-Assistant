# Báo cáo Phase 0

> Thực hiện: đêm 20 → 21/09/2026. Kế hoạch gốc: [phase-0.md](phase-0.md).
> **Kết luận: phần kỹ thuật đã hoàn thành và đã đẩy lên GitHub. Còn 3 việc của bạn (thư mentor, VPS, bảo vệ nhánh) chưa xong.**

## 1. Tóm tắt

| Hạng mục | Trạng thái |
|---|---|
| Repo cục bộ `D:\Intern-VSF\vsf-onboarding-assistant`, nối GitHub, có commit đầu | **Xong** |
| Tài liệu chuẩn tách khỏi bản lưu trữ; bộ dữ liệu test chạy được từ bản clone mới | **Xong** (đã kiểm bằng `git clone` thật) |
| Đẩy lên https://github.com/thufuture/VSF-Onboarding-Assistant (`main`) | **Xong**; `origin/main` trùng HEAD cục bộ |
| Thư gửi mentor | **Chưa** (việc của bạn; bản nháp ở Phụ lục B của [phase-0.md](phase-0.md)) |
| VPS + DuckDNS + trang `hello` qua HTTPS | **Chưa** (việc của bạn; chặn Phase 1b) |
| Bảo vệ nhánh `main`, secret scanning, xác nhận Private | **Chưa** (việc của bạn, trên giao diện GitHub) |

## 2. Kết quả cụ thể

| Mục | Giá trị |
|---|---|
| Thư mục | `D:\Intern-VSF\vsf-onboarding-assistant` |
| Remote | `origin` = https://github.com/thufuture/VSF-Onboarding-Assistant.git |
| Nhánh | `main` |
| Commit đầu | `d8195e2` — `chore: initial repository with design docs, plans and seed data` |
| Tác giả | `TranAnhThu <trananhthu270904@gmail.com>` (email git hiện tại, mặc định D3) |
| Số tệp trong commit | 94 (88 tệp trong `docs/chatbot-vsf/` + 6 tệp gốc) |
| Không có trong commit | `.venv`, `.env`, `__pycache__`, 5 PDF `real_public` (bị `.gitignore`), `ralion-*.md`, `gdoc_content.txt` |
| Nguồn `P-040` | **Không đổi**; chưa xóa gì |

Cấu trúc trong repo:

| Nhóm | Tệp |
|---|---|
| Chuẩn (`docs/chatbot-vsf/`) | PRD chuẩn, system design, database design, deployment-ci, `README.md`, `plan/`, `data/` |
| Lưu trữ (`docs/chatbot-vsf/archive/`) | `prd-v2.md`, `prd.docx` |
| Gốc | `.gitignore`, `.gitattributes`, `.env.example` (chỉ tên biến), `README.md`, `.github/CODEOWNERS`, `.github/pull_request_template.md` |

## 3. Các bước đã làm

| Bước | Nội dung | Kết quả |
|---|---|---|
| 1 | Tạo thư mục, `git init -b main`, thêm `origin` | Xong |
| 2 | Chép có chọn lọc bằng `robocopy` (mã thoát 3 = có tệp được chép, thuộc nhóm thành công 0–7) | Xong; 91 tệp chép + 2 tệp vào `archive/` |
| 3 | Tệp gốc | Xong |
| 4 | `generate_seed.py`: `LAB_DIRS` đọc từ biến môi trường `VSF_LAB_DIRS`; thêm ghi chú cảnh báo | Xong |
| 5 | `content_documents.py`: chuỗi khóa giả ghép lúc chạy bằng công thức **đúng** (`"AKIA" + "FAKE" * 3 + "1234"`, 20 ký tự) | Xong |
| 6 | `validate_seed.py`: coi `real_public` là tùy chọn (không lỗi khi thiếu tệp; bỏ kiểm chuỗi bắt buộc của câu phụ thuộc tài liệu đó) | Xong |
| 7 | README chỉ mục của bản chép: trỏ `archive/`, bỏ câu "chép vào `data/seed/`", thêm liên kết `plan/` | Xong |
| 8 | `.venv` và `pip install -r requirements.txt` | Xong |
| 9 | Kiểm chứng cục bộ | Xong (mục 5) |
| 10 | Quét bí mật | Xong: 0 kết quả |
| 11 | Commit cục bộ và clone thử bằng `git clone` thật, venv sạch | Xong |
| 12 | `git push -u origin main` | Xong, không bị chặn |
| 13 | Bật bảo vệ nhánh, secret scanning | **Chưa** (bạn) |
| 14 | Gửi thư mentor | **Chưa** (bạn) |
| 15 | Chuẩn bị VPS | **Chưa** (bạn) |

## 4. Điểm dừng và quyết định

| Điểm | Kết quả |
|---|---|
| CP1 (duyệt kế hoạch) | Bạn duyệt ("triển khai phase 0 đi") |
| CP2 (kiểm cục bộ) | Tôi báo cáo; bạn tiếp tục |
| CP3 (commit) và CP4 (đẩy) | Bạn xác nhận bằng "lên git này thufuture" kèm ảnh chụp tài khoản `thufuture` |
| CP5 (bảo vệ nhánh) | **Đang chờ bạn** |

| Quyết định | Đã dùng |
|---|---|
| D1 tên thư mục | `vsf-onboarding-assistant` (mặc định) |
| D2 môi trường Python | `.venv` trong repo (mặc định) |
| D3 email tác giả | Giữ email git hiện tại (mặc định); chưa gặp lỗi GH007 |
| D4 `real_public` | Chép vào bản làm việc, không commit (mặc định) |
| D5 nguồn `P-040` | Giữ nguyên (mặc định) |

## 5. Kiểm chứng đã chạy và kết quả

| Kiểm tra | Kết quả |
|---|---|
| `validate_seed.py` trên nguồn `P-040` (baseline) | 0 lỗi; 45 tệp; 242 câu (dev 165, test 77); 268 chuỗi bắt buộc |
| `validate_seed.py` trên bản làm việc (có `real_public`) | 0 lỗi, **khớp baseline** |
| `validate_seed.py` trên bản sao **không có** `real_public` | 0 lỗi; 5 ghi chú bỏ qua; A43 và A44 bỏ kiểm chuỗi; 265 chuỗi được kiểm (268 trừ 3 chuỗi của hai câu đó) |
| Phép thử âm: đổi tên một tệp `core` | Bị bắt (lỗi "thiếu file") |
| Phép thử âm: ghi thêm 1 byte vào một tệp `core` | Bị bắt (`sha256` không khớp manifest) |
| Hoàn nguyên hai phép thử | Xanh trở lại |
| E08: chuỗi khóa giả ghép trong mã so với chuỗi trong PDF đã sinh | Trùng khớp; không cần sinh lại tài liệu; hash manifest không đổi |
| Quét mẫu khóa/token (`AKIA…`, `sk-…`, `ghp_…`, `BEGIN PRIVATE KEY`, biến `*_KEY=` có giá trị) | 0 kết quả |
| Tệp không mong muốn trong cây | Không có |
| Khác biệt nguồn ↔ bản chép | Đúng 5 tệp đã sửa + thư mục `archive/` |
| Dry-run `git add -n` | 94 tệp; bỏ qua đúng `.venv`, `.env`, `real_public/` |
| `git clone` thật từ repo cục bộ, venv sạch, `pip install`, validator | 40 tệp PDF/DOCX; **0 lỗi**; hash một PDF khớp manifest sau chuẩn hóa xuống dòng |
| Sau đẩy: `git ls-remote` | `origin/main` = `d8195e2…` = HEAD cục bộ |

## 6. Sai lệch so với kế hoạch và ghi chú

1. **Hai lỗi thật của kế hoạch cũ đã được sửa** (đã nêu trong [phase-0.md](phase-0.md) mục 2): validator sẽ đỏ trên bản clone mới nếu không coi `real_public` là tùy chọn; và công thức ghép khóa giả cũ (`* 4`) sẽ ra 24 ký tự thay vì 20.
2. **Một sửa đổi thừa đã hoàn lại.** Khi bạn nói "dùng data mock", tôi thêm vào `generate_seed.py` việc giữ nguyên dòng manifest cũ khi thiếu `real_public`. Đó là mở rộng ngoài kế hoạch. Lần hoàn lại bị ngắt giữa chừng làm tệp tạm lỗi (`previous` không còn được định nghĩa), tôi đã hoàn tất việc hoàn lại và kiểm cú pháp. Trạng thái cuối chỉ có đúng thay đổi trong kế hoạch.
3. **Công cụ chặn một lệnh PowerShell** (nhận nhầm tham số `/E` của `robocopy` là đường dẫn xóa); tôi tách lệnh nhỏ hơn. Không ảnh hưởng kết quả.
4. **Cảnh báo CRLF khi `git add`:** nhiều tệp dữ liệu sinh trên Windows có CRLF ở bản làm việc; `.gitattributes` (`* text=auto eol=lf`) chuẩn hóa về LF trong repo. Bản clone dùng LF và vẫn qua validator, hash PDF khớp.
5. **Tệp `phase-0.md` trong repo đã lỗi thời.** Repo (commit `d8195e2`) chứa bản kế hoạch **trước khi thực hiện**. Sau đó ở `P-040` có thêm: `phase-0/` (bạn di chuyển `phase-0.md` vào đó), báo cáo này, `phase-1/phase-1.md`, và cập nhật liên kết trong `master-plan.md`, `README.md`. **Những thay đổi này chưa nằm trong repo**; sẽ đồng bộ ở commit kế tiếp khi bạn cho phép.
6. **Đã tạo rồi xóa 3 tệp cấu hình `backend/`** (Phase 1) khi bạn yêu cầu lập kế hoạch trước; repo vẫn sạch ở `d8195e2`.
7. **Thời gian thực hiện phần kỹ thuật** (tôi thao tác, không tính thời gian bạn duyệt): khoảng 30–40 phút liên tục, so với ước lượng 0,45 ngày công. Chưa đo chính xác; ghi lại làm dữ liệu hiệu chỉnh lịch **sau Phase 2**, nhưng chưa nên suy ra tốc độ chung vì Phase 0 chủ yếu là sao chép và kiểm tra.

## 7. Cổng hoàn thành ([phase-0.md](phase-0.md) mục 7)

- [x] `git remote -v` đúng URL; nhánh `main`.
- [x] `docs/chatbot-vsf/` có 5 tệp chuẩn + `plan/` + `data/`; `archive/` có đúng 2 tệp; không có `ralion-*.md`, `gdoc_content.txt`, `__pycache__`, `.env`, `.venv`.
- [x] `validate_seed.py` báo 0 lỗi cả trong thư mục làm việc và trong bản clone thử.
- [x] Kết quả trong thư mục làm việc giống baseline ở nguồn.
- [x] Quét bí mật 0 kết quả; mã nguồn không còn nguyên chuỗi khóa giả; nội dung E08 không đổi.
- [x] `P-040` không bị đổi ngoài các tệp tài liệu kế hoạch tôi thêm.
- [x] Đã đẩy lên `origin/main`; `git status` sạch; không bị chặn.
- [ ] Repo còn **Private**: bạn thấy "Private" trên giao diện ở ảnh chụp trước khi đẩy; **chưa xác nhận lại sau khi đẩy**.
- [ ] Thư mentor đã gửi.
- [ ] VPS: SSH bằng khóa được; `https://<tên>.duckdns.org` hiện trang `hello` qua HTTPS từ máy khác.

## 8. Còn lại

| # | Việc | Ai | Chặn gì | Cách làm |
|---|---|---|---|---|
| 1 | **VPS + DuckDNS + khóa SSH + trang `hello` qua HTTPS** | Bạn | **Phase 1b (ngày mai)** | [huong-dan-thiet-lap-may-chu.md](../huong-dan-thiet-lap-may-chu.md), 1–2 giờ |
| 2 | Gửi thư mentor | Bạn | Không chặn việc code; ảnh hưởng dữ liệu thật ở Phase 3 và 12b | Phụ lục B của [phase-0.md](phase-0.md); có thể gửi bản rút gọn 3 câu (bộ phận pilot, tài liệu thật khi nào, logo/tên) |
| 3 | Kiểm repo còn Private; bật bảo vệ nhánh `main` và secret scanning nếu gói cho phép | Bạn | Không chặn | Settings → Branches/Rules, Code security. Gói Free với repo private có thể không có; khi đó ghi giới hạn vào README (đã có sẵn dòng "chưa cấu hình") |
| 4 | Đồng bộ tài liệu kế hoạch mới vào repo và commit | Tôi, khi bạn nói | Không chặn | Chép `plan/` (kể cả `phase-0/`, `phase-1/`), cập nhật liên kết, commit; đẩy khi bạn xác nhận |
| 5 | Xóa bản nguồn ở `P-040` | Bạn, tùy chọn | Không | Không khuyến nghị vội: các tệp ở đó chưa được git theo dõi, xóa là mất hẳn |

## 9. Hạn chế đã biết (không sửa ở Phase 0)

- **Chỉ chạy `generate_seed.py` trên máy có `real_public/`.** Thiếu nó, các dòng `real_public` bị bỏ khỏi manifest và README, làm manifest đổi. Đã ghi vào `data/README.md`, README gốc và khuôn README trong `generate_seed.py`. Phase 3 sinh lại tài liệu trên máy có `real_public` ở `P-040`, hoặc đặt `VSF_LAB_DIRS`.
- Bản làm việc vẫn giữ 5 PDF `real_public` (không commit) nên trên máy này validator kiểm đủ, còn CI và bản clone sẽ bỏ qua.
- Repo GitHub chưa có CI và chưa có mã ứng dụng (đúng phạm vi Phase 0).

## 10. Phát hiện có ích cho phase sau (khi nghiên cứu Phase 1)

- **ParadeDB `v0.25.4-pg16`** có sẵn `pgvector 0.8.4`, `pg_search 0.25.4`, `btree_gist 1.7`; ràng buộc `EXCLUDE USING gist` theo khoảng ngày chạy đúng và từ chối bản chồng ngày.
- **Không ghi đè `command` của image:** lệnh mặc định đã nạp `pg_search,pg_cron,pg_stat_statements`; ghi đè thiếu `pg_cron` làm script khởi tạo lỗi. CI dùng được service container.
- **Model DeepSeek:** Ralion đang hard-code `deepseek-chat`, tên từng được lên lịch ngừng 2026-07-24; VSF dùng biến `LLM_MODEL` (mặc định `deepseek-flash`) và gọi thử ở đầu Phase 2.
- **Quick Tunnel của Cloudflare không hỗ trợ SSE**, nên không dùng làm đường lui cho chat.

Chi tiết ở [phase-1.md](../phase-1/phase-1.md).

## 11. Bước tiếp theo

1. **Bạn:** làm VPS (việc 1) trước ngày mai; gửi thư mentor khi tiện.
2. **Duyệt** [kế hoạch Phase 1](../phase-1/phase-1.md) và các quyết định P1–P10.
3. **Hôm nay (sau khi duyệt):** Phase 1a-A và 1a-B (khung cục bộ). **Ngày mai:** 1a-C (CI) và 1b (triển khai).
