# Phase 0 — Kế hoạch chi tiết (chưa thực hiện, chờ bạn duyệt)

> Trạng thái: **bản nháp để duyệt**. Chưa tạo thư mục, chưa chép, chưa sửa mã, chưa commit, chưa đẩy GitHub.
> Thuộc [master-plan.md](master-plan.md) (Phase 0 [Bắt buộc], ≈ 0,5 ngày công). Sau Phase 0 là Phase 1a.
> Tài liệu này chỉ mô tả việc sẽ làm; các đoạn mã bên dưới là **bản dự kiến**, chưa áp dụng vào đâu.

## 1. Mục tiêu và ranh giới

**Mục tiêu.** Có repo cục bộ `D:\Intern-VSF\vsf-onboarding-assistant` nối với https://github.com/thufuture/VSF-Onboarding-Assistant, chứa tài liệu chuẩn tách khỏi bản lưu trữ và bộ dữ liệu test chạy được ngay từ **bản clone mới**; có thư gửi mentor; VPS sẵn sàng cho Phase 1b.

| Làm ở Phase 0 | Không làm ở Phase 0 |
|---|---|
| Dựng repo cục bộ, chép tài liệu có chọn lọc | Không xóa hay sửa gì ở `P-040` (nguồn giữ nguyên) |
| Tệp gốc: `.gitignore`, `.gitattributes`, `README.md`, `.env.example`, mẫu PR, `CODEOWNERS` | Không viết mã backend/frontend (Phase 1a) |
| Sửa 3 tệp Python của bộ seed (mục 5, bước 4–6) | Không sinh lại tài liệu seed (không đổi hash trong manifest) |
| Kiểm chứng bằng bản **clone thử** trước khi đẩy | Không cấu hình CI (Phase 1a) |
| Soạn thư mentor và chuẩn bị VPS | Không đưa khóa DeepSeek/Modal vào bất kỳ tệp nào được commit |

## 2. Khảo sát hiện trạng (đã kiểm bằng lệnh chỉ đọc)

| Mục | Kết quả | Ảnh hưởng tới kế hoạch |
|---|---|---|
| Thư mục repo mới | Chưa tồn tại | Tạo mới, không sợ ghi đè |
| Công cụ | Git 2.50, Python 3.12, Node 22, Docker 29, OpenSSH có sẵn; **GitHub CLI (`gh`) chưa cài** | Đẩy code bằng `git` qua HTTPS, đăng nhập GitHub qua Git Credential Manager (đi kèm Git for Windows); không cần `gh` |
| Cấu hình git | `user.name = TranAnhThu`, `user.email = trananhthu270904@gmail.com`; `init.defaultBranch` chưa đặt; **`core.autocrlf = true` ở cấp hệ thống** | `git init -b main` rõ ràng; thêm `.gitattributes` để không đổi xuống dòng (xem rủi ro R3) |
| Gói Python | `pymupdf 1.28`, `python-docx 1.2`, `reportlab 5.0` đã cài; `Pillow` chưa thấy trong danh sách kiểm | Dùng `.venv` riêng và `pip install -r requirements.txt` để kiểm được từ môi trường sạch |
| Dữ liệu | Thư mục `chatbot-vsf` ≈ 22 MB, 92 tệp (bỏ `__pycache__`), 45 tệp PDF/DOCX; **không tệp nào > 500 KB ngoài `real_public/`** | Repo nhỏ, không cần Git LFS |
| Bộ seed nguồn | `validate_seed.py` chạy trên nguồn: **0 lỗi**, 242 câu vàng (dev 165, test 77) | Đây là mốc so sánh (baseline) |
| Đường dẫn tuyệt đối | Chỉ 2 chỗ: `generate_seed.py:27-28` (`LAB_DIRS` trỏ `D:/AI_Action_Lab/...`) và `builders.py:38` (`C:/Windows/Fonts`, chỉ là một mục trong danh sách tìm font) | Sửa `LAB_DIRS`; `builders.py` giữ nguyên |
| Khóa AWS giả | Chuỗi khóa giả nằm ở **một** chỗ trong mã nguồn: `content_documents.py` (tài liệu E08, gần dòng 504). Trong tệp PDF đã sinh **không** thấy chuỗi thô (nội dung nén) | Chỉ cần sửa mã nguồn; không cần sinh lại PDF |
| Chuỗi đó trong tài liệu `plan/` | Bản v4 của master-plan đã mô tả bằng lời, không còn nguyên chuỗi | Vẫn quét lại trước khi commit |
| `prd-v2.md` | Không có liên kết tương đối | Chuyển vào `archive/` không làm gãy liên kết |
| Xuống dòng | Tệp văn bản nguồn đều LF | Giữ LF bằng `.gitattributes` |
| Mật khẩu dev `ChangeMe!123` | Có trong `registry/users.json` và `content_registry.py` | Chỉ là mật khẩu dev của dữ liệu seed; Phase 11a chặn production dùng nó |

### Hai lỗi thật phát hiện khi khảo sát (cần sửa trong Phase 0)

**L1. Validator sẽ báo lỗi trên bản clone mới.** `data/.gitignore` bỏ qua `documents/real_public/` (5 PDF luật công khai, có file scan 12,5 MB không nên commit). Nhưng `manifests/documents_manifest.csv` vẫn liệt kê 5 tệp đó, và `validate_seed.py` (dòng ≈ 92) báo lỗi "thiếu file" cho **mọi** dòng manifest không tìm thấy tệp, không loại trừ `real_public`. Ngoài ra 2 câu vàng dev (A43, A44) cần tài liệu R01 (thuộc `real_public`) sẽ báo lỗi "chuỗi bắt buộc không nằm trong tài liệu". Hệ quả: ở máy bạn (đã chép `real_public`) validator xanh, nhưng ở bản clone mới và ở CI sẽ **đỏ 7 lỗi**. Bản kế hoạch trước ghi "thiếu `real_public` được phép" là **sai với mã hiện tại**. Sửa: coi `real_public` là tùy chọn trong validator (bước 6).

**L2. Công thức ghép chuỗi khóa giả trong bản kế hoạch trước sai.** Đã ghi `"AKIA" + "FAKE" * 4 + "1234"` sẽ ra chuỗi 24 ký tự, còn chuỗi gốc là `AKIA` + `FAKE` × **3** + `1234` (20 ký tự, khớp mẫu khóa AWS). Dùng công thức cũ sẽ làm đổi nội dung tài liệu E08. Công thức đúng ở bước 5.

**Hạn chế đã biết (không sửa ở Phase 0):** `generate_seed.py` khi chạy trên máy **thiếu** `real_public` sẽ bỏ các dòng `real_public` khỏi manifest và README, làm manifest bị đổi. Vì vậy chỉ chạy `generate_seed.py` trên máy có `real_public` (máy của bạn, Phase 3), và ghi cảnh báo này vào README của `data/`.

## 3. Các điểm dừng để bạn duyệt

| Điểm | Khi nào | Bạn xác nhận điều gì |
|---|---|---|
| **CP1** | Bây giờ | Duyệt kế hoạch này (kể cả quyết định D1–D5 ở mục 4) |
| **CP2** | Sau bước 9 (dựng xong, kiểm cục bộ) | Xem `git status`, danh sách tệp và kết quả kiểm; chưa commit |
| **CP3** | Trước bước 11 | Đồng ý commit đầu; chọn email tác giả (D3) |
| **CP4** | Trước bước 12 | Đồng ý đẩy lên GitHub (hành động ra ngoài) |
| **CP5** | Sau khi đẩy | Bạn tự bật bảo vệ nhánh trên GitHub nếu gói cho phép (bước 13) |

Ở mỗi điểm dừng, tôi không làm bước kế tiếp cho tới khi bạn nói.

## 4. Quyết định cần bạn chốt (mặc định in đậm)

| # | Quyết định | Mặc định đề xuất | Lựa chọn khác |
|---|---|---|---|
| D1 | Tên thư mục cục bộ | **`D:\Intern-VSF\vsf-onboarding-assistant`** | `VSF-Onboarding-Assistant` cho khớp tên GitHub (không ảnh hưởng gì) |
| D2 | Môi trường Python | **`.venv` trong repo (bị `.gitignore`)** | Dùng Python toàn cục |
| D3 | Email tác giả commit | Giữ email git hiện tại | Dùng email `noreply` của GitHub (nên nếu tài khoản bật "chặn push lộ email", xem R4) |
| D4 | Chép `real_public/` (≈ 13 MB, bị `.gitignore`) vào bản làm việc | **Có**, để cổng Phase 5 và câu A43/A44 dùng được | Không chép (validator vẫn xanh sau bước 6) |
| D5 | Thư mục nguồn ở `P-040` sau khi xong | **Giữ nguyên**; không tự xóa | Bạn tự xóa khi thấy đủ |

## 5. Các bước chi tiết

Lệnh viết cho **PowerShell**. Đường dẫn dùng biến `$SRC` và `$DST`.

```powershell
$SRC = "D:\Intern-VSF\P-040\docs\PlaningForOptimize\srs\chatbot-vsf"
$DST = "D:\Intern-VSF\vsf-onboarding-assistant"
```

### Bước 0 — Điều kiện tiên quyết

- Đã duyệt CP1; đăng nhập được GitHub bằng tài khoản `thufuture` trong trình duyệt.
- `git --version`, `python --version` chạy được (đã có).
- Chưa cần VPS ở bước này (làm song song, bước 15).

### Bước 1 — Tạo thư mục và khởi tạo git

```powershell
New-Item -ItemType Directory -Path $DST | Out-Null
Set-Location $DST
git init -b main
git remote add origin https://github.com/thufuture/VSF-Onboarding-Assistant.git
git remote -v
```

Chỉ ghi cấu hình cục bộ; **không** `fetch`/`push`. Mong đợi: `git remote -v` in hai dòng `origin` đúng URL.

### Bước 2 — Chép tài liệu có chọn lọc (sao chép, không di chuyển)

```powershell
New-Item -ItemType Directory -Path "$DST\docs\chatbot-vsf\archive" -Force | Out-Null
robocopy $SRC "$DST\docs\chatbot-vsf" /E /XD __pycache__ /XF *.pyc vsf-onboarding-assistant-prd-v2.md vsf-onboarding-assistant-prd.docx
Copy-Item "$SRC\vsf-onboarding-assistant-prd-v2.md","$SRC\vsf-onboarding-assistant-prd.docx" "$DST\docs\chatbot-vsf\archive\"
```

Ghi chú:
- `robocopy` trả mã thoát **0–7 là thành công** (không phải chỉ 0); mã ≥ 8 là lỗi.
- Chỉ chép nội dung của `chatbot-vsf\` nên `ralion-cv-interview-skill-gap-design.md`, `ralion-skill-gap-mvp-5-week-plan.md` và `gdoc_content.txt` (nằm ở nơi khác) **không** được chép.
- `data\documents\real_public\` được chép (D4) nhưng bị `data/.gitignore` bỏ qua khi commit.

Bảng kết quả mong đợi trong `docs\chatbot-vsf\`:

| Nhóm | Tệp/thư mục |
|---|---|
| Chuẩn | `vsf-onboarding-assistant-prd.md`, `…-system-design.md`, `…-database-design.md`, `…-deployment-ci.md`, `README.md` |
| Kế hoạch | `plan/` (gồm `phase-0.md` này) |
| Dữ liệu | `data/` (45 PDF/DOCX, `registry/`, `eval/`, `manifests/`, `tools/`) |
| Lưu trữ | `archive/vsf-onboarding-assistant-prd-v2.md`, `archive/vsf-onboarding-assistant-prd.docx` |

### Bước 3 — Tạo tệp gốc

Nội dung nháp ở **Phụ lục A**: `.gitignore`, `.gitattributes`, `README.md`, `.env.example`, `.github/pull_request_template.md`, `.github/CODEOWNERS`.

### Bước 4 — Sửa `data/tools/generate_seed.py` (chỉ bản chép)

Thay đường dẫn tuyệt đối bằng biến môi trường `VSF_LAB_DIRS`:

```diff
 import json
+import os
 import shutil
@@
-LAB_DIRS = [Path("D:/AI_Action_Lab/K3-Day08-RAG-Pipeline/data/landing/legal"),
-            Path("D:/AI_Action_Lab/DAY18_2A202601611_TranAnhThu/data")]
+# Thư mục chứa PDF luật công khai để chép vào documents/real_public/. Đặt biến môi trường
+# VSF_LAB_DIRS (nhiều đường dẫn, ngăn cách bằng dấu ; trên Windows hoặc : trên Linux/macOS). Mặc định rỗng.
+LAB_DIRS = [Path(p) for p in os.environ.get("VSF_LAB_DIRS", "").split(os.pathsep) if p.strip()]
```

Hành vi khi rỗng: `find_real_src` trả `None`, mã hiện có in "bỏ qua" cho từng tệp thiếu. Kèm cảnh báo về hạn chế ở mục 2 (thêm một dòng vào khuôn README trong `generate_seed.py` và cùng dòng đó vào `data/README.md` của bản chép, để hai nơi không lệch nhau).

### Bước 5 — Sửa `data/tools/content_documents.py` (chỉ bản chép)

Trong tài liệu E08, thay chuỗi khóa giả nằm trực tiếp trong câu bằng biến ghép lúc chạy. Công thức **đúng**:

```diff
+# Khóa truy cập giả dùng để kiểm thử cổng quét secret. Ghép lúc chạy để mã nguồn không chứa
+# nguyên chuỗi khớp mẫu khóa AWS; nội dung tài liệu sinh ra KHÔNG đổi.
+_FAKE_ACCESS_KEY = "AKIA" + "FAKE" * 3 + "1234"
@@ (trong tài liệu E08)
-            P("Để kết nối dịch vụ báo cáo, dùng khóa truy cập sau (khóa giả lập): <chuỗi khóa nguyên vẹn> và mật khẩu ..."),
+            P(f"Để kết nối dịch vụ báo cáo, dùng khóa truy cập sau (khóa giả lập): {_FAKE_ACCESS_KEY} và mật khẩu ..."),
```

Kiểm chứng đúng nội dung (không cần sinh lại PDF): giá trị của `_FAKE_ACCESS_KEY` phải có 20 ký tự, bắt đầu bằng `AKIA`, và **bằng** chuỗi mà PDF E08 đã có; so bằng cách trích chữ từ `SYN_E08_...pdf` bằng PyMuPDF rồi kiểm chuỗi con (lệnh ở Phụ lục D). Không chạy `generate_seed.py`, nên hash trong manifest không đổi.

### Bước 6 — Sửa `data/tools/validate_seed.py`: coi `real_public` là tùy chọn (chỉ bản chép)

Sửa L1 bằng hai thay đổi nhỏ:

```diff
+OPTIONAL_MISSING: set[str] = set()   # id tài liệu real_public không có mặt (không commit)
@@ trong check_documents(), thay khối "thiếu file"
         if not path.exists():
-            err(f"{rid}: thiếu file {r['relative_path']}")
+            if r["source_kind"] == "real_public":
+                OPTIONAL_MISSING.add(rid)
+                NOTES.append(f"{rid}: real_public không có mặt (không commit), bỏ qua")
+            else:
+                err(f"{rid}: thiếu file {r['relative_path']}")
             continue
@@ trong check_golden(), vòng lặp `for d in e.get("docs", [])`
+            skip_tokens = False
             for d in e.get("docs", []):
+                if d in OPTIONAL_MISSING:
+                    skip_tokens = True   # thiếu văn bản nguồn tùy chọn: bỏ kiểm chuỗi bắt buộc
+                    continue
@@
-            if rt in ("ANSWER", "GUIDE_PROCESS") and corpus:
+            if rt in ("ANSWER", "GUIDE_PROCESS") and corpus and not skip_tokens:
```

Hành vi mong đợi: **có** `real_public` → như cũ (kiểm đủ); **không có** → 5 ghi chú "bỏ qua", không lỗi, các câu A43/A44 không kiểm chuỗi (ghi chú). Tệp `real_public` có mặt vẫn được kiểm hash như bình thường. Vị trí chính xác của các đoạn này sẽ đối chiếu lại với tệp khi làm (số dòng có thể lệch vài dòng).

### Bước 7 — Sửa README chỉ mục bản chép

`docs/chatbot-vsf/README.md`:
- Mục "Tài liệu lịch sử": đường dẫn thành `archive/vsf-onboarding-assistant-prd-v2.md` và `archive/vsf-onboarding-assistant-prd.docx`.
- Bỏ câu "Khi tạo repo mới, chép `data/` vào `data/seed/`" (dữ liệu ở lại `docs/chatbot-vsf/data/`).
- Thêm dòng trỏ tới `plan/README.md`.

### Bước 8 — Môi trường Python

```powershell
Set-Location $DST
python -m venv .venv
.\.venv\Scripts\python -m pip install -r docs\chatbot-vsf\data\tools\requirements.txt
```

`.venv` bị `.gitignore`. Dùng để bước 9 và 10 chạy trong môi trường sạch, đúng như CI sau này.

### Bước 9 — Kiểm chứng cục bộ (kết thúc ở CP2)

```powershell
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\python docs\chatbot-vsf\data\tools\validate_seed.py
```

Mong đợi: `OK: 0 lỗi`, 45 tệp, 242 câu (dev 165, test 77), **giống baseline** ở nguồn. Rồi kiểm các mục ở Phụ lục D (quét bí mật, `git status`, không có tệp không mong muốn). Dừng ở **CP2**: bạn xem `git status` và danh sách tệp.

### Bước 10 — Quét bí mật trước khi commit

Quét toàn cây (trừ `.venv`, `real_public`) tìm mẫu khóa/token: `AKIA[0-9A-Z]{16}`, `sk-[A-Za-z0-9]{20,}`, `ghp_`/`github_pat_`, khối `BEGIN ... PRIVATE KEY`, và tên biến khóa có giá trị (`*_API_KEY=` khác rỗng). **Mong đợi: 0 kết quả.** Có kết quả thì dừng và xử lý trước khi tiếp tục. Không dùng tệp `.env` của Ralion và không sao chép nó vào repo.

### Bước 11 — Commit đầu cục bộ và clone thử (sau CP3)

Commit cục bộ **chưa đẩy đi đâu**. Cần có commit thì mới `git clone` thử được.

```powershell
Set-Location $DST
git add -A
git status            # xem lại lần cuối: không có .env, .venv, real_public, __pycache__
git commit -m "chore: initial repository with design docs, plans and seed data" -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

Rồi chạy **bản clone thử** để chứng minh L1 đã sửa (bản clone không có `real_public` vì bị `.gitignore`):

```powershell
git clone $DST "$env:TEMP\vsf-clone-test"
Set-Location "$env:TEMP\vsf-clone-test"
python -m venv .venv
.\.venv\Scripts\python -m pip install -r docs\chatbot-vsf\data\tools\requirements.txt
.\.venv\Scripts\python docs\chatbot-vsf\data\tools\validate_seed.py   # mong đợi: OK, 0 lỗi, 5 ghi chú bỏ qua real_public
```

Nếu clone thử báo lỗi: sửa ở `$DST`, `git commit --amend` (commit chưa đẩy nên sửa lại được), chạy lại clone thử. Chỉ sang bước 12 khi clone thử xanh.

### Bước 12 — Đẩy lên GitHub (sau CP4)

```powershell
Set-Location $DST
git push -u origin main
```

- Lần đầu, Git Credential Manager mở cửa sổ đăng nhập GitHub: đăng nhập tài khoản `thufuture`. **Không** dán token vào chat hay vào tệp.
- Repo GitHub đang trống nên nhánh `main` được tạo.
- Nếu bị chặn: xem rủi ro R1 và R4.

### Bước 13 — Sau khi đẩy (bạn làm trên giao diện GitHub, CP5)

- Settings → Branches (hoặc Rules): bật bảo vệ nhánh `main` (bắt buộc PR, chặn force-push) **nếu** gói cho phép; repo private ở gói Free có thể không có tính năng này, khi đó ghi giới hạn vào README gốc.
- Settings → Code security: bật secret scanning/push protection nếu có (gói Free với repo private có thể không có; kiểm trên giao diện).
- Xác nhận repo vẫn **Private**.

### Bước 14 — Gửi mentor (bạn gửi, nội dung nháp ở Phụ lục B)

Gửi ngay trong ngày đầu vì độ trễ phản hồi là bên ngoài.

### Bước 15 — Chuẩn bị VPS (bạn làm, song song)

Làm theo [huong-dan-thiet-lap-may-chu.md](huong-dan-thiet-lap-may-chu.md) tới bước "hello có HTTPS" (1–2 giờ). Chi tiết lựa chọn ở [phu-luc-may-chu-va-chi-phi.md](phu-luc-may-chu-va-chi-phi.md). Không đưa khóa Ralion lên VPS.

## 6. Việc của bạn và việc của tôi

| Bạn | Tôi |
|---|---|
| Duyệt kế hoạch (CP1); trả lời D1–D5 | Bước 1–11: tạo repo, chép, sửa 3 tệp Python, viết tệp gốc, kiểm chứng, commit |
| Xác nhận ở CP2, CP3, CP4 | Chạy clone thử và báo kết quả |
| Đăng nhập GitHub khi đẩy code; bật bảo vệ nhánh (bước 13) | Đọc kết quả và xử lý nếu bị chặn |
| Gửi thư mentor (bước 14) | Soạn thư (Phụ lục B) |
| Tạo VPS/DuckDNS/khóa SSH (bước 15) | Hướng dẫn và viết script từ Phase 1b |
| Tự chép khóa DeepSeek/Modal vào `.env` cục bộ khi tới Phase 2 | **Không đọc `.env` của Ralion**; chỉ tạo `.env.example` không có giá trị |

## 7. Cổng hoàn thành Phase 0

- [ ] `git remote -v` đúng URL; nhánh `main`.
- [ ] `docs/chatbot-vsf/` có 5 tệp chuẩn + `plan/` + `data/`; `archive/` có đúng 2 tệp; **không** có `ralion-*.md`, `gdoc_content.txt`, `__pycache__`, `.env`, `.venv`.
- [ ] `validate_seed.py` báo 0 lỗi **cả** trong thư mục làm việc **và** trong bản clone thử (bản clone không có `real_public`).
- [ ] Kết quả `validate_seed.py` trong thư mục làm việc giống baseline ở nguồn (45 tệp, 242 câu, dev 165, test 77).
- [ ] Quét bí mật: 0 kết quả; mã nguồn không còn nguyên chuỗi khóa giả; nội dung E08 không đổi.
- [ ] `P-040` không bị đổi (`git -C D:\Intern-VSF\P-040 status` chỉ còn các mục chưa theo dõi như trước).
- [ ] Đã đẩy lên `origin/main`, repo vẫn Private, `git status` sạch, không bị chặn.
- [ ] Thư mentor đã gửi (ghi ngày giờ).
- [ ] VPS: SSH bằng khóa được; `https://<tên>.duckdns.org` hiện trang `hello` qua HTTPS từ máy khác (hoặc ghi rõ đã dùng đường lui ở master-plan mục 5).

## 8. Rủi ro và cách xử lý

| # | Rủi ro | Xử lý |
|---|---|---|
| R1 | GitHub push protection chặn vì chuỗi giống khóa | Bước 5 và 10 đã loại chuỗi khỏi mã nguồn. Nếu vẫn bị chặn, đọc thông báo để biết tệp/dòng nào, sửa rồi commit lại; **không** tắt push protection. Với repo private gói Free, tính năng này có thể không hoạt động, nhưng vẫn xử lý để an toàn khi repo đổi sang public |
| R2 | `robocopy` báo thành công giả (mã 1–7) hoặc lỗi thật (≥ 8) | Đọc bảng mã thoát; đếm lại số tệp sau khi chép (92 tệp nguồn, trừ `__pycache__`) |
| R3 | Git đổi xuống dòng (CRLF↔LF) làm lệch hash | `.gitattributes` đặt `* text=auto eol=lf`, PDF/DOCX là `binary`; cần vì Git for Windows đang bật `core.autocrlf=true`. Kiểm bằng cách tính lại `sha256` của một PDF sau khi clone thử và so với manifest |
| R4 | Đẩy bị từ chối vì "private email" (GH007) | Dùng email `noreply` của GitHub cho repo này (`git config user.email ...` cục bộ), rồi sửa commit tác giả (`git commit --amend --reset-author`) nếu chưa đẩy |
| R5 | Đăng nhập nhầm tài khoản GitHub khi đẩy (tên git `TranAnhThu`, chủ repo `thufuture`) | Tên tác giả commit không cần khớp tài khoản; nhưng khi đăng nhập trình duyệt phải là `thufuture` hoặc tài khoản có quyền ghi vào repo |
| R6 | Sửa `validate_seed.py` làm lỏng kiểm tra ở chỗ khác | Chỉ áp dụng cho `source_kind == "real_public"`; chạy validator trên bản có `real_public` phải cho kết quả **y hệt** baseline; có thêm phép thử làm hỏng một tệp không phải `real_public` để chắc vẫn bị bắt |
| R7 | Đường dẫn dài/ký tự tiếng Việt trong tên tệp gây lỗi trên Windows | Tên tệp seed đã là ASCII; đường dẫn đích ngắn hơn nguồn; kiểm khi chép |
| R8 | Quên `.env` khi làm Phase 2 | `.gitignore` chặn `.env` và `.env.*` (trừ `.env.example`); quét bí mật ở bước 10 |
| R9 | Xóa nhầm nguồn ở `P-040` (các tệp chưa được git theo dõi, xóa là mất hẳn) | Kế hoạch không xóa gì; D5 giữ nguyên |

**Hoàn tác trước khi đẩy:** xóa thư mục `D:\Intern-VSF\vsf-onboarding-assistant` (và `%TEMP%\vsf-clone-test`); nguồn không bị ảnh hưởng. **Sau khi đẩy:** không ép ghi đè lịch sử; nếu có lỗi thì sửa bằng commit mới; nếu lỡ đẩy nhầm bí mật, coi khóa đó là đã lộ và thu hồi ngay.

## 9. Bàn giao cho Phase 1a

Sau Phase 0, Phase 1a bắt đầu từ một repo có: cây `docs/chatbot-vsf/`, `.gitignore`, `.gitattributes`, `.env.example`, `README.md`, mẫu PR, `CODEOWNERS`, và bộ seed kiểm chứng được từ bản clone. Việc đề xuất thêm cho Phase 1a (chưa làm ở đây): một job CI chạy `validate_seed.py` (nhanh, cần `pymupdf`, `python-docx`, `reportlab`).

---

## Phụ lục A — Nội dung nháp các tệp gốc

### `.gitignore`

```gitignore
# Bí mật và cấu hình cục bộ
.env
.env.*
!.env.example
*.pem
*.key

# Python
__pycache__/
*.pyc
.venv/
venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/

# Node / Next.js
node_modules/
.next/
out/

# Hệ điều hành / trình soạn thảo
.DS_Store
Thumbs.db
.idea/
.vscode/

# Nhật ký, dữ liệu chạy cục bộ
*.log
storage/
```

(`docs/chatbot-vsf/data/.gitignore` đã có sẵn và được giữ nguyên: `documents/real_public/`, `__pycache__/`, `*.pyc`, `_*.pdf`.)

### `.gitattributes`

```gitattributes
* text=auto eol=lf
*.sh text eol=lf
*.pdf binary
*.docx binary
*.png binary
*.jpg binary
*.webp binary
```

### `.env.example` (chỉ tên biến, không có giá trị bí mật)

```dotenv
# Sao chép thành .env (đã bị .gitignore). KHÔNG commit giá trị thật.
APP_ENV=development
APP_TIMEZONE=Asia/Ho_Chi_Minh

DATABASE_URL=postgresql+asyncpg://vsf:vsf@localhost:5432/vsf
SESSION_SECRET=

# LLM: DeepSeek qua giao diện tương thích OpenAI. Không hard-code tên model.
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-flash
LLM_API_KEY=

# Embedding: BGE-M3 trên Modal (đổi tên từ BGE_M3_* của Ralion)
EMBEDDING_PROVIDER=modal-bge-m3
EMBEDDING_ENDPOINT=
EMBEDDING_API_KEY=

STORAGE_PATH=./storage
CHAT_HISTORY_MESSAGES=6
RETENTION_CHAT_DAYS=90
RETENTION_TELEMETRY_DAYS=180
RETENTION_DEBUG_DAYS=30
CONTENT_GAP_MIN_USERS=2

# Chỉ dùng khi sinh lại bộ seed và muốn chép PDF luật công khai (ngăn cách bằng ; trên Windows)
VSF_LAB_DIRS=
```

Chuỗi kết nối `vsf:vsf@localhost` là mật khẩu DB cục bộ của môi trường dev, không phải bí mật; môi trường thật dùng giá trị riêng ở máy chủ.

### `.github/CODEOWNERS`

```text
* @thufuture
```

### `.github/pull_request_template.md`

```markdown
## Phase / mốc
<!-- Ví dụ: Phase 1a — khung cục bộ -->

## Thay đổi
-

## Cổng hoàn thành đã kiểm
- [ ] ruff / mypy / pytest / alembic check (backend)
- [ ] vitest / eslint / tsc / build (frontend)
- [ ] Đã cập nhật docs/chatbot-vsf/ nếu đổi thiết kế
- [ ] Không có bí mật, khóa hay dữ liệu thật trong thay đổi
- [ ] Không sửa migration đã áp dụng

## Ghi chú rủi ro
```

### `README.md` (gốc)

Nội dung: tên và mục đích dự án (trợ lý onboarding cho nhân sự mới, trả lời có nguồn, chỉ đúng quy trình); **trạng thái** ("đang ở Phase 0/1a, bản demo thực tập, chưa phải sản phẩm chính thức"); liên kết tới PRD chuẩn, thiết kế, `plan/README.md`; bảng chuẩn/lưu trữ; cách kiểm bộ seed (`validate_seed.py`, kèm cảnh báo về `real_public` và `generate_seed.py`); nhắc "dữ liệu seed là **giả lập**, nhãn SYNTHETIC"; hướng dẫn tạo `.env` từ `.env.example`; ghi rõ nếu không bật được bảo vệ nhánh.

## Phụ lục B — Thư gửi mentor (nháp, bạn tự gửi)

> Chào anh Trí, em đã chốt phạm vi và dựng xong bộ dữ liệu thử giả lập cho chatbot onboarding. Để làm tiếp ở giai đoạn thật, em xin anh hỗ trợ vài việc:
>
> **1. Ba việc em cần anh quyết định**
> - Bộ phận nào làm pilot, và ai là owner để xác nhận nội dung?
> - Anh có cấp được tài liệu/quy trình onboarding thật không, dự kiến khi nào, dạng file nào?
> - Em có được dùng tên/logo Vin/VSF trên trang giới thiệu không, hay để nhãn "bản demo thực tập"?
>
> **2. Dữ liệu em cần từ VSF** (theo PRD mục 8)
> - Lộ trình và quy trình onboarding chung đã xác nhận.
> - Hướng dẫn ngày đầu, hồ sơ, chính sách, danh bạ đầu mối.
> - Danh sách tình huống cần HR/IT/VinSOC xử lý.
> - Mẫu form/ticket thật (trường bắt buộc, hàng đợi nhận, trạng thái).
> - Danh mục link chính thức, kèm owner và ngày xác nhận.
> - Điều kiện rẽ nhánh thật theo bộ phận/địa điểm/thiết bị.
> - 80–120 câu hỏi thực tế của người mới.
>
> **3. Lưu ý về hạ tầng và dữ liệu**
> - Hiện em demo trên máy chủ cá nhân, **chỉ chứa dữ liệu giả lập**. Nếu dùng tài liệu thật, em cần anh duyệt nơi lưu trữ.
> - Hệ thống gọi dịch vụ ngoài để tạo câu trả lời và vector hóa (DeepSeek, Modal). Với dữ liệu thật, em cần anh xác nhận có được gửi ra dịch vụ ngoài không.
>
> Em cảm ơn anh.

(Chỉnh giọng văn theo cách bạn xưng hô với mentor.)

## Phụ lục C — Kiểm chứng: bản đối chiếu trước/sau

| Kiểm tra | Nguồn `P-040` | Repo mới (làm việc) | Bản clone thử |
|---|---|---|---|
| Số tệp PDF/DOCX trong `documents/` | 45 | 45 (gồm `real_public`) | 40 (không có `real_public`) |
| `validate_seed.py` | 0 lỗi | 0 lỗi | 0 lỗi, 5 ghi chú bỏ qua `real_public` |
| Câu vàng | 242 (dev 165, test 77) | giống | giống (A43, A44 bỏ kiểm chuỗi, ghi chú) |
| Hash `SYN_E08_...pdf` | theo manifest | giống nguồn | giống nguồn |
| Chuỗi khóa giả nguyên vẹn trong `.py` | có | **không** | **không** |

## Phụ lục D — Lệnh kiểm tra (dự kiến)

```powershell
# 1. Đếm tệp sau khi chép (nguồn: 92 tệp không tính __pycache__)
(Get-ChildItem "$DST\docs\chatbot-vsf" -Recurse -File | Where-Object { $_.FullName -notmatch "__pycache__" }).Count

# 2. Không có tệp không mong muốn
Get-ChildItem $DST -Recurse -Force -File | Where-Object { $_.FullName -notmatch "\\\.git\\|\\\.venv\\" -and $_.Name -match "^(\.env|gdoc_content\.txt|ralion-.*\.md)$" }

# 3. Mã nguồn không còn chuỗi khóa AWS nguyên vẹn (mong đợi: không có kết quả)
Select-String -Path "$DST\docs\**\*.py","$DST\docs\**\*.md" -Pattern "AKIA[0-9A-Z]{16}" -Recurse

# 4. Nội dung E08 không đổi: chữ trong PDF vẫn chứa khóa giả 20 ký tự bắt đầu bằng AKIA
.\.venv\Scripts\python -c "import pymupdf,re; t=''.join(p.get_text() for p in pymupdf.open(r'docs\chatbot-vsf\data\documents\ingest_defects\SYN_E08_Huong_dan_ket_noi_he_thong_co_secret.pdf')); m=re.search(r'AKIA[0-9A-Z]{16}', t); print('OK' if m and len(m.group(0))==20 else 'SAI', m.group(0)[:4] if m else '')"

# 5. Công thức ghép trong mã ra đúng độ dài và tiền tố
.\.venv\Scripts\python -c "k='AKIA'+'FAKE'*3+'1234'; print(len(k), k[:4])"   # mong đợi: 20 AKIA

# 6. Hash PDF không bị đổi bởi xuống dòng (so với manifest)
Get-FileHash "$DST\docs\chatbot-vsf\data\documents\core\SYN_D02_Noi_quy_trang_phuc.pdf" -Algorithm SHA256
```

## Phụ lục E — Thứ tự thực hiện và thời gian ước tính

| Bước | Nội dung | Ước lượng |
|---|---|---|
| 1–2 | Dựng thư mục, git, chép | 0,05 ngày |
| 3, 7 | Tệp gốc, README chỉ mục | 0,1 ngày |
| 4–6 | Sửa 3 tệp Python | 0,1 ngày |
| 8–10 | Môi trường, kiểm chứng, quét bí mật | 0,1 ngày |
| 11–13 | Commit, clone thử, đẩy, bảo vệ nhánh | 0,1 ngày |
| 14–15 | Thư mentor, VPS (bạn làm, song song) | không tính vào ngày công của tôi; VPS 1–2 giờ |
| | **Tổng phần của tôi** | **≈ 0,45 ngày** |
