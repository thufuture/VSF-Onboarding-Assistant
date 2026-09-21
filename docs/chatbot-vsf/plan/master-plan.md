# VSF Onboarding Assistant — Kế hoạch phase (1 người, timebox 4 tuần)

> Trạng thái: **bản nháp v4 để duyệt**. v2: sửa theo nhận xét vòng 1 của Codex; v3: đưa triển khai vào 4 tuần; **v4: sửa theo nhận xét vòng 2** (migration, route, versioning link, provider, timebox). **Phase 0 đã thực hiện phần kỹ thuật** (báo cáo: [phase-0/bao-cao-phase-0.md](phase-0/bao-cao-phase-0.md)); các phase còn lại chưa thực hiện.
> Repo đích: https://github.com/thufuture/VSF-Onboarding-Assistant (private, đang trống).
> PRD chuẩn: [../vsf-onboarding-assistant-prd.md](../vsf-onboarding-assistant-prd.md). Tài liệu này không thay thế thiết kế; nó xếp thứ tự, gắn mốc, cổng kiểm và nói rõ cái gì bắt buộc, cái gì là stretch.

## 1. Cách đọc

- Mỗi phase có khung: **Mục tiêu / Việc / Đầu ra / Cổng hoàn thành / Phụ thuộc / Rủi ro**. Mọi phase làm **tuần tự** (một người).
- Nhãn **[Bắt buộc]** = thuộc technical MVP; **[Stretch]** = làm nếu còn thời gian, theo thứ tự ưu tiên ở mục 3.
- Thiết kế chi tiết: [system design](../vsf-onboarding-assistant-system-design.md) (M0–M6, hợp đồng route ở mục 9.1), [database design](../vsf-onboarding-assistant-database-design.md) (migration ở mục 7), [deployment-ci](../vsf-onboarding-assistant-deployment-ci.md) (D0–D5). Không chép lại ở đây.
- Con số chất lượng (Recall@5 ≥ 85%, …) là **mục tiêu** của PRD mục 10, chưa phải kết quả đã đo.

## 2. Tổng quan và timebox

**4 tuần là timebox mục tiêu, không phải cam kết hoàn thành production.** Phạm vi bắt buộc là technical MVP chạy đầu-cuối và có một bản demo trên máy chủ thật. Landing, tự động deploy, diễn tập khôi phục và pilot là stretch.

| Phase | Tên | Mốc thiết kế | Ngày công | Loại |
|---|---|---|---:|---|
| 0 | Repo, tài liệu chuẩn/lưu trữ, xin dữ liệu thật, chuẩn bị VPS | mới | 0,5 | Bắt buộc |
| 1a | Khung cục bộ: repo, Compose, CI, `/api/v1/health` | M0 | 1 | Bắt buộc |
| 1b | Khung triển khai: máy chủ chạy `/api/v1/health` qua HTTPS (**giới hạn cứng 1 ngày**) | D0–D2 | 1 | Bắt buộc, có đường lui |
| 2 | Lát cắt dọc: 1 tài liệu → tìm kiếm → trả lời có nguồn; `0001_core` đầy đủ | mới (chạm M2–M4) | 3 | Bắt buộc |
| 3 | Dữ liệu: rà tay, đóng băng golden test | mới | 1 | Bắt buộc |
| 4 | Xác thực và trang đăng nhập (tái dùng Ralion) | M1 | 1,5 | Bắt buộc |
| 5 | Ingest hoàn chỉnh | M2 | 2,5 | Bắt buộc |
| 6 | Registry, tìm kiếm quy trình, harness đánh giá (`0002_registry`) | M3 | 2,5 | Bắt buộc |
| 7 | Lõi chat 6 loại phản hồi và ticket (`0003_chat`, `0004_tickets`) | M4 | 3 | Bắt buộc |
| 8 | Giao diện tối thiểu | M5 (rút gọn) | 1,5 | Bắt buộc |
| 9 | Đánh giá và báo cáo | M6 | 1 | Bắt buộc |
| 11a | Deploy thủ công bản cuối + cấu hình an toàn | D3–D4 (một phần) | 0,5 | Bắt buộc |
| 12a | Demo nghiệm thu, bảng đối chiếu PRD mục 11 | mới | 0,4 | Bắt buộc |
| 10 | Landing tiếng Việt, tối giản | mới | 0,5 | **Stretch** |
| 11b | `release.yml` tự động, rollback tự động, diễn tập khôi phục | D3–D4 | 0,5 | **Stretch** |
| 12b | Pilot nhỏ (chỉ khi có dữ liệu/người thử được duyệt) | mới | 0,1 | **Stretch** |
| | **Bắt buộc: 19,4 · Stretch: 1,1 · Tổng** | | **20,5** | |

**Nói thẳng.**
- Ước lượng chưa hiệu chỉnh. **Đo lại sau Phase 2**; nếu Phase 2 mất quá 4 ngày công thì bắt đầu cắt theo mục 3.
- Đệm thực chất chỉ là các mục stretch (≈ 1 ngày). Khoảng dao động thực tế của một người là **4–6 tuần**. Nếu tự động deploy, landing hoặc pilot là **bắt buộc**, hãy coi mốc là 5–6 tuần.
- Phase 1 chứa nhiều rủi ro hạ tầng nhất; vì vậy tách 1a/1b và đặt giới hạn cứng cho 1b.
- Bản đầu có 40,5–45,5 ngày công nhưng ghi lịch 5–6 tuần; các bản sau cắt phạm vi thay vì kéo dài lịch (mục 9).

**Lịch tuần (tương đối).**

| Tuần | Phase | Demo cuối tuần |
|---|---|---|
| 1 | 0, 1a, 1b, 2 (phần đầu) | CI xanh; `https://<host>/api/v1/health` trả `ok` (hoặc đường lui); hỏi 1 câu về tài liệu nghỉ phép nhận câu trả lời có trích dẫn |
| 2 | 2 (còn lại), 3, 4, 5 (phần đầu) | Đăng nhập; golden test đã đóng băng; upload tài liệu vào hàng đợi |
| 3 | 5 (còn lại), 6, 7 (phần đầu) | Registry nạp và kiểm; số đo đầu tiên trên golden dev; chat nhiều loại phản hồi qua API |
| 4 | 7 (còn lại), 8, 9, 11a, 12a; stretch: 10, 11b, 12b | Đủ 6 loại và ticket; luồng chính trên giao diện; bảng so sánh; bản demo trên máy chủ; nghiệm thu |

## 3. Cắt phạm vi

**Không thể cắt:** ingest, tìm kiếm, chat 6 loại, validator, số đo trên golden test, các chỉ số an toàn bằng 0.

**Đã cắt sẵn so với bản đầu:** baseline B2; hàng đợi ticket trên giao diện (chỉ API); landing 0,5 ngày; giao diện 1,5 ngày.

**Thứ tự cắt thêm khi trễ (từ trên xuống):**
1. Stretch: Phase 10 (landing) → 11b → 12b.
2. Sửa registry trên giao diện → chỉ xem; đổi qua API/JSON nạp lại (cổng Playwright của Phase 8 đổi sang API).
3. Duyệt/diff tài liệu trên giao diện → API và CLI.
4. Phase 1b vượt 1 ngày → dừng, deploy thủ công dời sang 11a (xem đường lui ở mục 5).

**Ngoài 4 tuần (sau MVP):** timer sao lưu định kỳ và đẩy ra ngoài máy chủ (D4 đầy đủ), giám sát và cảnh báo (D5), Terraform, tách production, Dependabot; giao diện tiếng Anh, A/B ingest, trang "thiếu tài liệu", dashboard Langfuse, pilot quy mô thật, SSO, đổi mật khẩu bắt buộc.

## 4. Quy ước chung

- Mỗi phase là một hoặc vài PR nhỏ vào `main`; không commit thẳng `main` sau Phase 0 (nếu gói GitHub không cho bảo vệ nhánh, giữ quy ước bằng tay).
- Gate tối thiểu: backend `ruff`, `mypy`, `pytest`, `alembic check`; frontend `vitest`, `eslint`, `tsc`, `build`. Thêm dần khi có mã (Phase 1a chỉ cần ruff, mypy, pytest, tsc, build).
- Đổi thiết kế thì sửa `docs/chatbot-vsf/` trong cùng PR.
- Không đưa bí mật vào repo (chỉ `*.env.example`). Dữ liệu seed là **giả lập**, gắn nhãn `SYNTHETIC`; không trình bày như chính sách thật của VSF.
- Chỉnh prompt và tham số bằng golden **dev**; golden **test** chỉ để báo cáo số cuối.
- **MVP chỉ có tiếng Việt**; giữ cấu trúc `messages/vi.json` để thêm `en` sau.
- **Migration:** mỗi migration áp dụng một lần, không sửa migration đã áp dụng. `0001_core` viết đầy đủ ở Phase 2; `0002_registry` ở Phase 6; `0003_chat` và `0004_tickets` ở Phase 7. **Không có bảng `sessions`** (phiên là cookie HMAC + `users.session_invalid_before`).
- **Hợp đồng route** ([system design mục 9.1](../vsf-onboarding-assistant-system-design.md)): `/` → `/vi`; giao diện ở `/vi/login`, `/vi/chat`, `/vi/admin/...`; toàn bộ backend ở `/api/v1/*`; `/api/v1/health` công khai; `/api/v1/ready*` chỉ nội bộ (Caddy trả 404 từ ngoài). Không có `/health` hay `/ready` ở gốc.

## 5. Quyết định kỹ thuật và hạ tầng đã chốt

| Hạng mục | Quyết định |
|---|---|
| Embedding | **BGE-M3 trên Modal**, dùng lại `modal_bge_m3/app.py` và endpoint của Ralion. Biến của VSF: `EMBEDDING_PROVIDER`, `EMBEDDING_ENDPOINT`, `EMBEDDING_API_KEY` (khi chép từ `.env` của Ralion: `BGE_M3_ENDPOINT` → `EMBEDDING_ENDPOINT`, `BGE_M3_API_KEY` → `EMBEDDING_API_KEY`). Đặt **budget/spend limit** của workspace Modal ([Modal Budgets](https://modal.com/docs/guide/budgets)) |
| LLM | **DeepSeek** qua giao diện tương thích OpenAI: `LLM_BASE_URL=https://api.deepseek.com`, `LLM_MODEL=deepseek-flash`, `LLM_API_KEY`. Dùng chế độ **JSON output** ([DeepSeek API docs](https://api-docs.deepseek.com/)) và kiểm kết quả bằng schema Pydantic, thử lại một lần nếu JSON hỏng. **Không hard-code tên model**: Ralion đang dùng `deepseek-chat`, tên mà DeepSeek từng lên lịch ngừng vào 2026-07-24; [trang Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing/) hiện nêu `deepseek-flash` và `deepseek-v4-pro`. Gọi thử `LLM_MODEL` ngay đầu Phase 2. Đổi nhà cung cấp chỉ cần đổi biến môi trường |
| Khóa và bí mật | Khóa DeepSeek và khóa/endpoint Modal **đã có ở Ralion**. Dùng ở **máy cục bộ** bằng cách bạn tự chép giá trị vào `.env` của repo mới (đã bị `.gitignore`; **tôi không đọc `.env` của Ralion**). **Không đưa khóa Ralion lên VPS cá nhân**: trước Phase 1b/11a tạo khóa DeepSeek riêng và (nên) triển khai bản Modal riêng cho VSF, mỗi cái có hạn mức chi tiêu. Lý do: chi phí và hạn mức không lẫn với Ralion, thu hồi một bên không làm hỏng bên kia, và khóa của một dự án nhóm không nằm trên máy chủ cá nhân. Kiểm khóa thuộc quyền dùng của bạn |
| Kiểm thử và CI | **Embedding giả xác định** và **LLM giả**; CI không bao giờ gọi API trả phí. Chưa có khóa LLM ở Phase 2: chạy LLM giả cho contract test; **chất lượng câu trả lời chưa được tính** tới khi có khóa thật |
| Máy chủ | **Chính: Oracle Cloud Always Free** (ARM A1.Flex, 1–2 OCPU / 4–6 GB, thử nghiệm; Oracle có thể thu hồi máy nhàn rỗi và có lúc hết máy, xem [phụ lục](phu-luc-may-chu-va-chi-phi.md)). **Dự phòng: Hetzner Cloud CX23** (2 vCPU / 4 GB / 40 GB), thuê 1 tháng rồi xóa (Hetzner [tính tiền cả khi tắt máy](https://docs.hetzner.com/cloud/billing/faq/)). Tạo máy Oracle quá khoảng 1 giờ không được thì chuyển sang Hetzner |
| Tên miền | `<tên>.duckdns.org` (miễn phí); **không dùng `sslip.io` cho HTTPS** |
| CI/CD | GitHub Actions (runner của GitHub; gói Free có [2.000 phút/tháng cho repo private](https://docs.github.com/en/actions/concepts/billing-and-usage)); image lên GHCR ([billing](https://docs.github.com/en/billing/concepts/product-billing/github-packages)) |
| Dữ liệu trên VPS | Chỉ dữ liệu **giả lập**; dữ liệu thật của VSF chỉ đưa lên khi mentor duyệt nơi lưu trữ |
| Đường lui nếu chưa có máy chủ ở 1b | Demo cục bộ (không có URL công khai); hoặc chế độ chat **không stream** (một POST trả `result` JSON) nếu phải đi qua tunnel. **Quick Tunnel của Cloudflare không hỗ trợ SSE** ([tài liệu](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/)) |

So sánh nhà cung cấp, chi phí và bảng "đủ hay không" ở [phu-luc-may-chu-va-chi-phi.md](phu-luc-may-chu-va-chi-phi.md); thao tác từng bước ở [huong-dan-thiet-lap-may-chu.md](huong-dan-thiet-lap-may-chu.md).

## 6. Tài liệu chuẩn và lưu trữ

| Loại | Tệp | Vị trí trong repo mới |
|---|---|---|
| **Chuẩn** | `vsf-onboarding-assistant-prd.md`, `…-system-design.md`, `…-database-design.md`, `…-deployment-ci.md`, `README.md`, `data/`, `plan/` | `docs/chatbot-vsf/` |
| **Lưu trữ** (chỉ tra cứu lịch sử) | `vsf-onboarding-assistant-prd-v2.md`, `vsf-onboarding-assistant-prd.docx` | `docs/chatbot-vsf/archive/` |
| **Không chép** | `ralion-cv-interview-skill-gap-design.md`, `ralion-skill-gap-mvp-5-week-plan.md`, `gdoc_content.txt` | — |

Khi mâu thuẫn, PRD chuẩn thắng.

---

## Phase 0 — Repo, tài liệu chuẩn/lưu trữ, xin dữ liệu thật [Bắt buộc]

Kế hoạch từng bước, điểm dừng duyệt, mã dự kiến và thư mentor nháp: [phase-0/phase-0.md](phase-0/phase-0.md). **Báo cáo kết quả (đã hoàn thành gì, còn gì):** [phase-0/bao-cao-phase-0.md](phase-0/bao-cao-phase-0.md).

**Mục tiêu.** Repo cục bộ nối GitHub, tài liệu chuẩn tách khỏi bản lưu trữ, kiểm được từ repo mới; yêu cầu dữ liệu thật gửi mentor **ngay ngày đầu**; VPS sẵn sàng.

**Việc.**
1. Tạo `D:\Intern-VSF\vsf-onboarding-assistant`, `git init -b main`, `git remote add origin https://github.com/thufuture/VSF-Onboarding-Assistant.git`.
2. **Chép có chọn lọc** (không di chuyển) theo mục 6; bỏ `__pycache__/`; sửa README bản chép trỏ đúng `archive/`. Nguồn ở P-040 giữ nguyên tới khi bạn xác nhận (các file này chưa được git theo dõi, xóa là mất hẳn).
3. `.gitignore` gốc (Python, Node, `.env`, `.next/`, `node_modules/`), giữ `.gitignore` của `data/` (bỏ qua `documents/real_public/`).
4. `LAB_DIRS` trong `data/tools/generate_seed.py` (đường dẫn tuyệt đối `D:/AI_Action_Lab/...`) → biến môi trường `VSF_LAB_DIRS`, mặc định rỗng.
5. **Chuỗi khóa giả:** `content_documents.py` (dòng 504) chứa một khóa truy cập giả dạng khóa AWS (tiền tố `AKIA` + 16 ký tự) để test quét secret; dạng này có thể bị GitHub push protection chặn. Ghép chuỗi lúc chạy để mã nguồn không chứa nguyên chuỗi khớp mẫu; nội dung tài liệu sinh ra không đổi. Quét toàn repo (kể cả tài liệu `plan/`) tìm chuỗi này trước khi commit; nếu vẫn bị chặn thì thêm ngoại lệ có ghi chú, không tắt push protection.
6. `README.md` gốc, `.env.example` (chỉ tên biến: `LLM_*`, `EMBEDDING_*`, `SESSION_SECRET`, `DATABASE_URL`…), mẫu PR, `CODEOWNERS`; tạo `.env` cục bộ (đã bị `.gitignore`) và **tự chép** giá trị khóa DeepSeek/Modal từ Ralion vào đó.
7. **Gửi mentor danh sách xin dữ liệu thật** (PRD mục 8) và hỏi các việc chặn: bộ phận pilot; có tài liệu thật không, khi nào; có được dùng logo/tên Vin-VSF không; ghi rõ máy chủ demo là VPS cá nhân chỉ chứa dữ liệu giả lập.
8. **Chuẩn bị máy chủ:** làm theo [huong-dan-thiet-lap-may-chu.md](huong-dan-thiet-lap-may-chu.md) tới bước container `hello` có HTTPS (1–2 giờ). **Không dùng lại VM của Ralion.**
9. Bật bảo vệ nhánh `main` và secret scanning nếu gói GitHub cho phép; nếu không, ghi giới hạn vào README.
10. Commit đầu và đẩy lên `origin/main`. **Đẩy lên GitHub là hành động ra ngoài; cần bạn xác nhận ngay trước khi chạy.**

**Đầu ra.** Repo có commit đầu; `docs/chatbot-vsf/` (chuẩn) và `archive/` (lưu trữ); tin nhắn đã gửi mentor; VPS + hostname sẵn sàng.

**Cổng hoàn thành.** Từ repo mới: `python docs/chatbot-vsf/data/tools/validate_seed.py` báo 0 lỗi **trên cả bản clone mới** (cần sửa validator để coi `real_public` là tùy chọn: mã hiện tại báo lỗi khi thiếu, xem phase-0.md mục 2 và bước 6); `git status` sạch; push không bị chặn; không có `ralion-*.md`/`gdoc_content.txt`; `https://<tên>.duckdns.org` hiện trang `hello` qua HTTPS từ máy khác.

**Phụ thuộc.** Không.

**Rủi ro.** Push protection; chép sót/lẫn bản cũ; không đăng ký được VPS (xác minh thẻ/danh tính) → dùng đường lui ở mục 5; nguồn ở P-040 chưa có lịch sử git.

---

## Phase 1a — Khung cục bộ [Bắt buộc]

Kế hoạch chi tiết (1a-A backend, 1a-B frontend, 1a-C CI): [phase-1/phase-1.md](phase-1/phase-1.md). **Trạng thái (2026-09-21): 1a-A và 1a-B đã làm và kiểm chứng cục bộ (nhánh `phase-1a-skeleton`, chưa commit); 1a-C (CI) và 1b (triển khai) chưa làm.** Báo cáo: [phase-1/bao-cao-phase-1.md](phase-1/bao-cao-phase-1.md).

**Mục tiêu.** Khung chạy ở máy cục bộ và CI xanh.

**Việc.**
1. Cây backend theo [system design mục 3](../vsf-onboarding-assistant-system-design.md) (`api/routers, services, dto, model, core, infrastructure, ai`), chỉ tạo cái cần dùng ngay.
2. `docker-compose.yml` với ParadeDB (Postgres 16): bật `pgvector`, `pg_search`, `btree_gist` (kiểm `CREATE EXTENSION`); một biến `PARADEDB_TAG` dùng chung.
3. FastAPI khung: `GET /api/v1/health`, `GET /api/v1/ready`; Alembic khung (chưa có migration nghiệp vụ).
4. Frontend Next.js khung (`output: standalone`) với `messages/vi.json`, token thiết kế ([system design mục 11](../vsf-onboarding-assistant-system-design.md)); `/` chuyển hướng `/vi`; rewrite `/api/*` chỉ cho dev.
5. CI tối thiểu (GitHub Actions): ruff, mypy, pytest, tsc, build.

**Cổng hoàn thành.** CI xanh trên `main`; `docker compose up` rồi `curl http://localhost:<cổng>/api/v1/health` trả `ok`; ba extension tạo được trong container.

**Phụ thuộc.** Phase 0. **Rủi ro.** Image ParadeDB thiếu extension (kiểm ngay); lệch phiên bản Next.js/next-intl (khóa lockfile).

---

## Phase 1b — Khung triển khai [Bắt buộc, giới hạn cứng 1 ngày]

Kế hoạch chi tiết: [phase-1/phase-1.md](phase-1/phase-1.md) mục 8.

**Mục tiêu.** Một bản khung chạy trên máy chủ thật qua HTTPS để rủi ro hạ tầng lộ sớm ([deployment-ci mục 0](../vsf-onboarding-assistant-deployment-ci.md)).

**Việc.**
1. **D0:** `bootstrap.sh` trên VPS (Docker, `ufw` 22/80/443, SSH chỉ khóa, người dùng deploy riêng).
2. `backend/Dockerfile`, `frontend/Dockerfile` (multi-stage, không root; một image backend dùng cho `backend`/`worker`/`migrate`); `deploy/compose.vps.yml`.
3. `deploy/Caddyfile` theo hợp đồng route: `/api/*` → backend, còn lại → frontend, **chặn `/api/v1/ready*` từ ngoài**, HTTPS tự động, một origin.
4. **D2:** `deploy.sh` bản đầu (kéo image, migrate, khởi động, chờ `/api/v1/ready` nội bộ, smoke test) và `smoke-test.sh`; đẩy image lên GHCR (workflow đơn giản hoặc lệnh tay); chạy `deploy.sh` tay.

**Cổng hoàn thành.** Từ máy khác: `/api/v1/health` = 200 `ok`, `/vi/login` = 200 (trang khung), `/` chuyển hướng tới `/vi`, `/api/v1/ready` từ ngoài = 404; ba extension tạo được trên máy chủ; không có secret trong image hay repo.

**Đường lui nếu quá 1 ngày.** Dừng phần còn lại, tiếp tục Phase 2 cục bộ, dời deploy thủ công sang Phase 11a. Ghi lý do (DNS, chứng chỉ, extension, RAM) vào nhật ký để 11a không lặp lại lỗi.

**Phụ thuộc.** Phase 1a; VPS + DuckDNS từ Phase 0. **Rủi ro.** 4 GB RAM không đủ (đo, nâng gói nếu cần và ghi lại); Let's Encrypt/DuckDNS; lỗi kiến trúc CPU (Oracle là ARM: build đa kiến trúc `linux/amd64` + `linux/arm64`, kiểm ảnh nền có bản arm64); Oracle hết máy hoặc thu hồi máy nhàn rỗi (chuyển Hetzner, dựng lại bằng compose + seed); quy tắc `iptables` trong máy Oracle chặn 80/443.

---

## Phase 2 — Lát cắt dọc: 1 tài liệu → trả lời có nguồn [Bắt buộc]

**Mục tiêu.** Chứng minh **lõi** chạy đầu-cuối trước khi xây các tầng xung quanh; đo tốc độ thật để hiệu chỉnh lịch.

**Việc.**
1. Chọn `SYN_D03b` (nghỉ phép v2024, DOCX) và 8–10 câu golden loại `ANSWER` chỉ dựa vào tài liệu này, thêm 2 câu ngoài tài liệu (ví dụ chỗ ngồi ngày mai).
2. **Viết `0001_core` đầy đủ** theo [database design mục 7](../vsf-onboarding-assistant-database-design.md) (extension, `users`, `teams`, `team_members`, bảng tài liệu kèm exclusion constraint, HNSW, BM25, `jobs`, `audit_logs`). Chỉ DDL và mô hình; **không** viết lại ở các phase sau.
3. Parse (MarkItDown) → chunk → embedding BGE-M3 1024 chiều (Modal; **embedding giả** trong test) → HNSW cosine + BM25.
4. Hybrid search (RRF k=60) trả top-k chunk.
5. **Gọi thử `LLM_MODEL` (`deepseek-flash`) trước khi viết mã**; nếu tên model bị từ chối, đối chiếu [Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing/) rồi đổi biến. Một lời gọi LLM (DeepSeek, chế độ JSON output; **LLM giả** trong test) trả JSON `{answer, quote, chunk_id}`, kiểm bằng schema Pydantic (thử lại một lần nếu hỏng); kiểm tối thiểu: `quote` là chuỗi con nguyên văn của chunk, nếu không → "chưa có căn cứ".
6. Trang chat tối giản ở `/vi/chat` (chỉ bật khi `ENV=dev`, bị khóa ở Phase 4).
7. Đo và ghi: độ trễ p50/p95, RAM (`docker stats`), **giờ công thật**; kiểm lát cắt chạy trên máy chủ nếu 1b đã xong.

**Cổng hoàn thành.** `alembic upgrade head` áp dụng `0001_core` sạch, `alembic check` xanh; với LLM (DeepSeek) và embedding (Modal) **thật**: ≥ 8/10 câu `ANSWER` đúng và trích dẫn thật, 2 câu ngoài tài liệu không bịa; với LLM/embedding **giả**: contract test xanh (chất lượng chưa tính); số đo độ trễ và giờ công đã ghi.

**Phụ thuộc.** Phase 1a. Khóa DeepSeek và endpoint/khóa Modal (đã có ở Ralion, chép vào `.env` cục bộ). **Rủi ro.** ParadeDB hybrid query khó hơn dự kiến (lý do làm sớm); lát cắt phình thành "làm luôn Phase 5" (giữ đúng 1 tài liệu); chi phí API (đã đặt hạn mức).

---

## Phase 3 — Dữ liệu: rà tay và đóng băng [Bắt buộc]

**Mục tiêu.** Bộ dữ liệu đủ tin để đo: nội dung dài do LLM viết **chưa có người rà**, và golden test phải được bảo vệ.

**Việc.**
1. Đọc tay 8–10 tài liệu đại diện (D03b, D04, D08b, D12, P01, P06, P08, PUBSUM_V01, PUBSUM_V02): dấu tiếng Việt, mâu thuẫn dữ kiện, câu vô nghĩa, nhãn `SYNTHETIC`. Ghi lỗi vào bảng nhỏ.
2. Sửa ở **mã nguồn sinh** (`data/tools/long_*.py`, `content_*.py`) rồi chạy lại `generate_seed.py`; không sửa tay PDF/DOCX (manifest có hash).
3. Rà 30 câu golden ngẫu nhiên: nhãn đúng, câu tự nhiên, `must_include` hợp lý.
4. **Đóng băng golden test** (77 câu): ghi hash `golden_test.jsonl`; không dùng để chỉnh prompt.
5. Chốt danh sách xin dữ liệu thật và trạng thái phản hồi của mentor.
6. **Về `real_public/`:** thư mục này **không được commit** (repo mới và CI sẽ không có `PUB_R05`). Mọi cổng bắt buộc dùng file được commit (ví dụ `SYN_E01` cho ca PDF scan). Các file `real_public` chỉ kiểm khi có mặt.

**Cổng hoàn thành.** `validate_seed.py` 0 lỗi sau khi sửa; ≥ 8 tài liệu có ghi nhận đã rà; hash golden test đã ghi.

**Phụ thuộc.** Phase 0, 2. **Rủi ro.** Rà tay vượt 1 ngày (giữ giới hạn 8–10 tài liệu); mentor chưa phản hồi → kết luận cuối chỉ nói được "kỹ thuật chạy đúng trên dữ liệu giả lập".

---

## Phase 4 — Xác thực và trang đăng nhập (M1) [Bắt buộc]

Chi tiết giao diện: [frontend-login-reuse.md](frontend-login-reuse.md).

**Mục tiêu.** Đăng nhập email + mật khẩu, có vai trò; trang `/vi/login` tái dùng từ Ralion.

**Việc.**
1. **Mở rộng và dùng** các bảng danh tính đã có trong `0001_core` (`users`, `teams`, `team_members`, cột `users.session_invalid_before`). **Không tạo bảng `sessions`, không tạo `0001` lần hai.**
2. Băm mật khẩu (scrypt), cookie httpOnly ký HMAC `uid.iat.exp.sig` (chép có chọn lọc từ Ralion rồi chỉnh), thu hồi bằng `session_invalid_before`, giới hạn thử sai.
3. Vai trò: nhân viên mới, HR/Owner, quản trị; kiểm quyền ở tầng `api`.
4. `/api/v1/auth/*` ([system design mục 9](../vsf-onboarding-assistant-system-design.md)); nạp tài khoản dev từ `registry/users.json`.
5. Trang `/vi/login` chép từ Ralion và chỉnh (thương hiệu, token, chữ ra `messages/vi.json`); nối `authApi`; chuyển trang theo vai trò (`/vi/chat`, `/vi/admin`); bộ chặn `?next=` kèm test mở rộng. **Không chép** `X-User-Id`/`localStorage` của Ralion.
6. Khóa trang chat tạm của Phase 2 sau đăng nhập.
7. Test: đăng nhập sai, hết hạn, thu hồi, trái vai trò; yêu cầu chỉ có `X-User-Id` bị từ chối.

**Cổng hoàn thành.** Pytest xanh; đăng xuất/thu hồi làm cookie cũ bị từ chối ngay; Playwright: đăng nhập tài khoản dev tới đúng trang theo vai trò; `grep` không thấy `X-User-Id`, `ralion-demo-user-id`, "Ralion" trong mã VSF; production từ chối khởi động nếu còn mật khẩu dev.

**Phụ thuộc.** Phase 2 (`0001_core`). **Rủi ro.** Mật khẩu dev lọt vào môi trường thật; yêu cầu SSO (ngoài 4 tuần).

---

## Phase 5 — Ingest hoàn chỉnh (M2) [Bắt buộc]

**Mục tiêu.** Upload PDF/DOCX/MD, tự chuyển thành nội dung chuẩn, tách section/chunk, gợi ý tìm kiếm, người upload duyệt.

**Việc.** Theo [system design mục 5.1](../vsf-onboarding-assistant-system-design.md), mở rộng từ Phase 2 (bảng đã có trong `0001_core`):
1. Phiên bản tài liệu và ràng buộc `EXCLUDE USING gist` trên khoảng hiệu lực; múi giờ Asia/Ho_Chi_Minh.
2. Upload trả **202**, việc vào hàng đợi Postgres, worker xử lý.
3. Cổng chất lượng: quét secret, từ chối file bí mật, file hỏng, tệp giả đuôi `.pdf`, PDF scan cần OCR.
4. Section (cha)/chunk (con); tóm tắt, câu hỏi mẫu, từ đồng nghĩa làm **gợi ý tìm kiếm** (không bao giờ làm trích dẫn).
5. Vòng đời duyệt; diff qua API.
6. **CLI nạp seed** đọc `docs/chatbot-vsf/data/`, dùng `manifests/documents_manifest.csv` (`expected_ingest`); chạy được trong container.

**Cổng hoàn thành.** Nạp `core` thành công; hai bản chồng ngày bị **DB** từ chối; bản có hiệu lực tương lai không làm mất bản hiện tại; mỗi file trong `ingest_defects` bị từ chối đúng lý do; **`SYN_E01` (scan tổng hợp, được commit) được nhận diện là PDF scan cần OCR**; nếu `PUB_R05` có mặt thì cũng phải vậy.

**Phụ thuộc.** Phase 2, 3, 4. **Rủi ro.** Dịch vụ embedding ngoài; DOCX bảng gộp ô (pack `format_edge` bắt); chunk tốt trên dữ liệu giả lập không đảm bảo tốt trên tài liệu thật.

---

## Phase 6 — Registry, tìm kiếm quy trình, harness đánh giá (M3) [Bắt buộc]

**Mục tiêu.** Quy trình, link, đầu mối, form là dữ liệu có cấu trúc HR quản lý được; tìm kiếm trả nguồn đúng; có công cụ đo.

**Việc.** Theo [system design mục 5.2 và 6](../vsf-onboarding-assistant-system-design.md):
1. **`0002_registry`:** `contact_channels`, `approved_links` (có `code`, `version_no`, `UNIQUE (code, version_no)`, ràng buộc chống hai bản `APPROVED` chồng hiệu lực), `forms`, `procedures`; bất biến INV15/17/18. Quy trình tham chiếu link bằng **`link_codes`**; nạp `data/registry/*.json` với `key` → `code`.
2. Kiểm toàn vẹn registry; fixture `registry/invalid/` bị bắt đúng lỗi.
3. Hybrid search trên tài liệu **và** quy trình; lọc theo ACTIVE/APPROVED và ngày hiệu lực (`as_of`).
4. Harness đọc `data/eval/golden_dev.jsonl`/`golden_test.jsonl`; in Recall@5, đúng loại phản hồi, đúng đầu mối/form.
5. Ngưỡng chỉ số thành cổng CI (tập rẻ mỗi PR; tập đầy đủ chạy thủ công).

**Cổng hoàn thành.** Chỉ số tái lập (hai lần chạy cùng số); ngưỡng CI lấy từ **số đo thật của lần chạy đầu**; mọi fixture `invalid` bị bắt; đổi URL một link (phiên bản mới) làm mọi quy trình dùng link đó dùng URL mới mà không sửa quy trình.

**Phụ thuộc.** Phase 5. **Rủi ro.** Golden tự viết dễ "học vẹt" (test tách hẳn); điều kiện rẽ nhánh thật chỉ có khi có dữ liệu thật.

---

## Phase 7 — Lõi chat 6 loại phản hồi và ticket (M4) [Bắt buộc]

**Mục tiêu.** Mỗi lượt hỏi trả đúng một trong sáu loại, có nguồn, không bịa dữ liệu cá nhân, ticket chỉ gửi sau xác nhận.

**Việc.** Theo [system design mục 7 và 8](../vsf-onboarding-assistant-system-design.md):
1. **`0003_chat`** và **`0004_tickets`**.
2. Định tuyến song song **trong một lượt hỏi**: một lời gọi LLM gộp phân loại + trích slot + viết lại câu, chạy cùng tìm kiếm.
3. Sáu loại: `ANSWER`, `GUIDE_PROCESS`, `ASK_CLARIFICATION`, `OFFER_TICKET`, `NO_BASIS` (`no_evidence`, `expired_only`, `insufficient_evidence`, `conflicting_sources`), `OUT_OF_SCOPE`.
4. Hợp đồng có cấu trúc; validator kiểm trích dẫn, `link_codes` (phân giải thành bản `APPROVED` đang hiệu lực), đầu mối, form.
5. Slot ngữ cảnh ở `conversations.context`; cửa sổ trí nhớ 4–6 tin nhắn.
6. Ticket `DRAFT → SUBMITTED`, chỉ gửi sau `POST /tickets/{id}/confirm`.
7. SSE `progress` rồi `result`; **thêm chế độ không stream** (`Accept: application/json` trả một `result`), dùng cho test và tunnel. Caddy không được đệm SSE (kiểm ở 11a).
8. Telemetry không lưu nội dung; móc che nội dung cho Langfuse (chưa dashboard); `llm_call_logs` không chứa nội dung; job dọn dữ liệu theo ba lớp riêng tư (chat 90 ngày, telemetry 180 ngày, debug capture 30 ngày, chỉ khi đồng ý); chỉ **lưu** dữ liệu "thiếu tài liệu" (≥ 2 người), chưa có trang.
9. Không dùng LangChain/LangGraph.

**Cổng hoàn thành.** Ca "Tôi thuộc Vinmec… cài Ubuntu sao?" → `GUIDE_PROCESS` rồi `OFFER_TICKET`; "mai tôi ngồi chỗ nào?" không nêu số bàn; các chỉ số an toàn bằng **0** trên golden dev: bịa dữ liệu cá nhân, ticket gửi khi chưa xác nhận, ticket cho câu ngoài phạm vi, link chưa duyệt.

**Phụ thuộc.** Phase 6. **Rủi ro.** Độ trễ (đo p50/p95); prompt injection từ tài liệu (pack `injection` là ca kiểm); chi phí LLM; SSE bị proxy đệm.

---

## Phase 8 — Giao diện tối thiểu (M5 rút gọn) [Bắt buộc]

**Việc.** Theo [system design mục 11](../vsf-onboarding-assistant-system-design.md), chỉ tiếng Việt:
1. Chat đầy đủ: `progress`, panel nguồn, thẻ ticket (nháp, xác nhận, hủy).
2. Tài liệu: upload, trạng thái ingest, bản chuyển đổi, diff dạng văn bản, duyệt.
3. Registry: xem tất cả; **sửa link và đầu mối** bằng form đơn giản (thực thể còn lại chỉ xem).
4. Ticket: **chỉ API**.
5. Playwright cho luồng chính.

**Cổng hoàn thành.** Playwright: HR tạo phiên bản mới của một link hoặc đổi một đầu mối và bot dùng bản mới ở lượt kế; nhân viên hỏi → có nguồn → mở panel nguồn; hoàn tất một ticket nháp → xác nhận.

**Phụ thuộc.** Phase 7. **Rủi ro.** Giao diện quản trị phình ra (làm bảng đơn giản; cắt theo mục 3); SSE lỗi giữa chừng (có đường thử lại).

---

## Phase 9 — Đánh giá và báo cáo (M6) [Bắt buộc]

**Việc.** Theo [PRD mục 10](../vsf-onboarding-assistant-prd.md): B0 (mô tả), B1 (từ khóa), Proposed; **không làm B2** trong 4 tuần. Chạy trên golden **test** (77 câu): Recall@5, có căn cứ và trích dẫn đúng, đúng loại phản hồi, đúng đầu mối/form, chỉ số an toàn; phân tích lỗi; báo cáo vào `docs/chatbot-vsf/` (kể cả chỗ không đạt).

**Cổng hoàn thành.** Bảng B1 và Proposed trên cùng tập test; mỗi số ghi "đo trên bộ **giả lập**"; không dùng mục tiêu thay số đo; nêu rõ thiếu B2 nên chưa tách được phần đóng góp của định tuyến quy trình.

**Phụ thuộc.** Phase 7 (Phase 8 khuyến nghị). **Rủi ro.** Kết quả tốt trên dữ liệu giả lập bị hiểu thành "đúng với VSF thật"; vô tình chỉnh theo golden test.

---

## Phase 11a — Deploy thủ công bản cuối + cấu hình an toàn [Bắt buộc]

**Việc.** Theo [deployment-ci mục 6, 7, 12](../vsf-onboarding-assistant-deployment-ci.md):
1. Hoàn thiện `deploy.sh`: `flock` chống deploy chồng, **backup DB trước migrate**, `rollback.sh` thủ công (chạy lại image trước).
2. Bí mật ở `/opt/vsf/env/*.env` (không qua GitHub); **validator cấu hình production** từ chối khởi động nếu `SESSION_SECRET` yếu/mặc định hoặc còn mật khẩu dev; tài khoản demo có mật khẩu riêng.
3. Deploy bản cuối bằng tay; nạp seed bằng CLI (Phase 5); smoke test công khai theo hợp đồng route; kiểm **SSE không bị Caddy đệm** và vài câu golden qua HTTPS.
4. Cứng hóa: HSTS và header bảo mật, giới hạn body upload, không publish cổng DB/backend.

**Cổng hoàn thành.** Từ máy khác vào `https://<host>/vi/login`, đăng nhập tài khoản demo, hỏi một câu nhận trả lời có nguồn; production từ chối khởi động với `SESSION_SECRET` mặc định; `grep` không thấy secret trong repo hoặc lớp image.

**Phụ thuộc.** Phase 1b (hoặc làm bù nếu 1b bị cắt), 5, 8. **Rủi ro.** Gỡ lỗi hạ tầng lâu hơn dự kiến; RAM 4 GB; dữ liệu thật chưa được phép lên VPS cá nhân.

## Phase 11b — Tự động hóa và khôi phục [Stretch]

`release.yml` (push `main` → verify → build → GHCR theo digest → SSH `deploy.sh` → kiểm sau deploy; Environment `staging` chỉ nhánh `main`); rollback tự động khi smoke test hỏng; diễn tập khôi phục một lần (`backup-db.sh` → `restore-db.sh` vào DB tạm). **Cổng:** merge một PR nhỏ → máy chủ tự chạy bản mới; cố tình làm hỏng smoke test → rollback tự chạy; restore thành công.

## Phase 10 — Landing tiếng Việt, tối giản [Stretch]

Chi tiết: [landing-page-plan.md](landing-page-plan.md). Ảnh minh họa có giấy phép, không ngụ ý văn phòng VSF; nút "Bắt đầu hỏi" → `/vi/login`. **Cổng:** Lighthouse ≥ 90; Playwright 375/1280 px; mọi ảnh có dòng trong `CREDITS.md`. Trước khi làm phase này, `/vi` chuyển hướng tới `/vi/login` hoặc `/vi/chat`.

## Phase 12 — Demo nghiệm thu

**12a [Bắt buộc]:** bảng đối chiếu [PRD mục 11](../vsf-onboarding-assistant-prd.md), mỗi tiêu chí ghi rõ **đã chứng minh trên dữ liệu giả lập** hay **cần dữ liệu thật mới kết luận được**; demo với mentor qua địa chỉ HTTPS (hoặc cục bộ nếu 1b/11a bị cắt); danh sách việc sau MVP. **Cổng:** clone mới làm theo README chạy được `docker compose up` cục bộ. **Phụ thuộc bắt buộc:** Phase 9 và 11a. **Phụ thuộc tùy chọn:** Phase 10.
**12b [Stretch]:** pilot nhỏ (2–3 người thử) **chỉ khi** mentor cấp dữ liệu/người thử **và** nơi lưu trữ được duyệt; ghi phản hồi hữu ích/không.

---

## 7. Rủi ro chung

| Rủi ro | Giảm thiểu |
|---|---|
| Ước lượng chưa hiệu chỉnh, gần như không đệm | Đo sau Phase 2; cắt theo mục 3; không thêm phạm vi |
| Không có VPS hoặc máy chủ phải là của VSF | Đường lui ở mục 5; hỏi mentor từ Phase 0 |
| Chưa có tài liệu thật | Xin từ Phase 0; báo cáo nói rõ giới hạn |
| Seed và golden tự viết | Rà tay ở Phase 3; tách dev/test; đóng băng test |
| Chi phí và độ trễ LLM/embedding | Hạn mức chi tiêu ở nhà cung cấp và Modal; fake trong CI |
| Tên model DeepSeek đổi hoặc ngừng (Ralion đang hard-code `deepseek-chat`, tên từng lên lịch ngừng 2026-07-24) | `LLM_MODEL` là biến môi trường; gọi thử ngay đầu Phase 2; đối chiếu trang Models & Pricing chính thức |
| Dùng chung khóa Ralion cho dự án khác | Chỉ dùng cục bộ; khóa riêng có hạn mức trước khi lên VPS; không đưa khóa vào repo, tài liệu hay chat |
| Dữ liệu thật gửi ra dịch vụ ngoài (DeepSeek, Modal) | Chỉ dữ liệu giả lập cho tới khi mentor duyệt; ghi rõ trong báo cáo pilot |
| Extension hoặc RAM thiếu trên máy chủ | Kiểm ở Phase 1a/1b |
| Dữ liệu thật lên VPS cá nhân | Chỉ dữ liệu giả lập; dữ liệu thật cần mentor duyệt nơi lưu trữ |
| Ảnh và thương hiệu Vin | Ảnh có giấy phép, chú thích "minh họa"; xin mentor trước khi dùng logo |
| Prompt injection từ tài liệu | Coi tài liệu là dữ liệu; pack `injection` bắt buộc |
| Dữ liệu cá nhân trong chat | Ba lớp dữ liệu; telemetry không nội dung; job dọn |

## 8. Câu hỏi mở

1. ~~Nhà cung cấp LLM/embedding~~ **Đã chốt (2026-09-20):** DeepSeek + Modal BGE-M3, khóa lấy từ Ralion dùng cục bộ (mục 5). Còn mở: DeepSeek chạy máy chủ ở nước ngoài, nên **dữ liệu thật của VSF chỉ gửi tới DeepSeek/Modal khi mentor duyệt**; dữ liệu giả lập thì không vấn đề. (Phase 12b)
2. Bộ phận pilot, owner và thời điểm mentor cấp tài liệu thật. (Phase 3, 12b)
3. Được dùng logo/tên Vin-VSF trên landing không, ai duyệt? (Phase 10)
4. Gói GitHub hiện tại có bảo vệ nhánh cho repo private không? (Phase 0)
5. Sau MVP có cần tiếng Anh, SSO, đổi mật khẩu bắt buộc, sao lưu định kỳ, giám sát không? (ngoài 4 tuần)

## 9. Thay đổi so với các bản trước

**v2 (nhận xét vòng 1):** cắt phạm vi vì bản đầu 40,5–45,5 ngày công nhưng ghi lịch 5–6 tuần; bỏ "song song"; landing về cuối; MVP chỉ tiếng Việt; thêm lát cắt dọc (Phase 2) và Phase dữ liệu (Phase 3); chép tài liệu có chọn lọc, bản cũ vào `archive/`; ảnh Vincom chỉ minh họa. Không theo Codex về 8–10 tuần vì mâu thuẫn ràng buộc 3–4 tuần.

**v3:** đưa triển khai vào 4 tuần; bù bằng cách rút landing, giao diện, bỏ B2.

**v4 (nhận xét vòng 2, tất cả đã đối chiếu với file thật):**

| Điểm | Kết quả | Sửa |
|---|---|---|
| Migration `0001` và bảng `sessions` | Đúng: DB design không có `sessions`, `0001_core` gồm cả bảng tài liệu | Bỏ `sessions`; `0001_core` viết đầy đủ ở Phase 2; Phase 4 dùng lại; sửa cả system design M1 |
| 4 cardinality | Đúng | Sửa trong database design |
| `ApprovedLink` chưa versioning | Đúng | Thêm `code`, `version_no`; quy trình tham chiếu bằng `link_codes` (database design, system design) |
| Provider chưa chốt | Đúng | Mục 5: Modal BGE-M3, DeepSeek (`deepseek-flash`) qua giao diện tương thích OpenAI, fake trong CI, hạn mức chi tiêu; khóa Ralion chỉ dùng cục bộ |
| Gate `PUB_R05` | Đúng một phần (file có ở máy này nhưng không commit) | Gate dùng `SYN_E01`; `PUB_R05` chỉ khi có mặt |
| Route và Caddy | Đúng, là lỗi vận hành | Hợp đồng route mới; `/api/v1/health` công khai, `/api/v1/ready*` nội bộ; sửa system design, deployment-ci |
| Phase 12 phụ thuộc landing | Đúng | Phụ thuộc bắt buộc 9 và 11a; 10 tùy chọn |
| Timebox 4 tuần | Đúng | Timebox mục tiêu; bắt buộc/stretch; 1b có giới hạn cứng |
| `master-plan.md` quá dài, nguồn blog | Đúng | Tách phụ lục; chỉ dùng nguồn chính thức |
| (Phát hiện thêm) Quick Tunnel không hỗ trợ SSE | Đúng theo tài liệu Cloudflare | Đường lui đổi; thêm chế độ chat không stream |
