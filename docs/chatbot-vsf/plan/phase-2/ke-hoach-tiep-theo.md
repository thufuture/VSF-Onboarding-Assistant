# Kế hoạch tiếp theo của Phase 2 — chi tiết (chưa thực hiện, chờ bạn duyệt)

> Sau CP-2A ([bao-cao-phase-2.md](bao-cao-phase-2.md)). Nền: [phase-2.md](phase-2.md) (kế hoạch gốc, 8 quyết định D1–D8, bộ 10 câu hỏi, cổng hoàn thành), [landing-page-plan.md](../landing-page-plan.md), [frontend-login-reuse.md](../frontend-login-reuse.md).
> Theo yêu cầu của bạn: **làm giao diện landing và đăng nhập trước, rồi các chức năng backend, chạy song song hai luồng và có checkpoint riêng cho từng luồng.** Mọi đoạn mã ở đây là bản dự kiến.

## 0. "Song song" nghĩa là gì với một người làm

Hai luồng không phụ thuộc nhau, nên tôi làm **xen kẽ** và đổi luồng khi một luồng bị chặn (ví dụ chờ khóa DeepSeek/Modal thì chuyển sang giao diện). Chỉ có một điểm nối: trang chat (giao diện) gọi endpoint chat (backend); trang chat được làm bằng dữ liệu giả trước, đến 2-E mới nối thật.

| Luồng | Nội dung | Checkpoint |
|---|---|---|
| **UI** | U1 landing, U2 đăng nhập (vỏ), U3 chat (giả) | CP-U1 (sau U1+U2), CP-U2 (sau U3) |
| **Backend** | 2-B nạp tài liệu, 2-C tìm kiếm, 2-D LLM và validator, 2-E endpoint | CP-2B, CP-2C, CP-2D |
| **Kết thúc** | Nối UI với backend, đo, báo cáo | CP-2F |

## 1. Thứ tự đề xuất và thời gian

| Thứ tự | Việc | Ước lượng | Checkpoint |
|---|---|---|---|
| 1 | **U1** Landing page | 0,5 ngày | |
| 2 | **U2** Trang đăng nhập (vỏ, có kiểm tra nhập liệu) | 0,4 ngày | **CP-U1**: bạn xem landing và đăng nhập trên trình duyệt |
| 3 | **2-B** Nạp tài liệu | 0,75 ngày | **CP-2B**: xem section/chunk/embedding trong DB |
| 4 | **2-C** Tìm kiếm hybrid (mở đầu bằng spike 30 phút) | 0,5 ngày | **CP-2C**: xem kết quả tìm kiếm với embedding thật |
| 5 | **2-D** LLM và validator | 0,5 ngày | **CP-2D**: xem trả lời thật và validator chặn quote bịa |
| 6 | **U3** Trang chat giả, rồi **2-E** nối endpoint thật | 0,4 ngày | **CP-U2**: bạn thử chat thật từ trình duyệt |
| 7 | **2-F** Đo, báo cáo, cập nhật tài liệu | 0,25 ngày | **CP-2F** |
| | **Cộng** | **≈ 3,3 ngày** | Phase 2 (2-B đến 2-F) ≈ 2,4 ngày + 2-A đã xong 0,75 ngày + giao diện ≈ 1,3 ngày (đưa lên sớm từ Phase 4 và Phase 10) |

Ước lượng chưa hiệu chỉnh. Nếu tổng Phase 2 (2-A đến 2-F, không tính giao diện) vượt **4 ngày** thì cắt theo master-plan mục 3.

## 2. Quyết định cần bạn chốt (mặc định in đậm)

**Về giao diện**

| # | Quyết định | Mặc định | Lựa chọn khác |
|---|---|---|---|
| U-D1 | Giọng văn landing | **Xưng "bạn"** | "em" như VLearn |
| U-D2 | Ảnh hero | **Nền gradient theo token, chừa khung ảnh**; chỉ đặt ảnh Vincom Center Đồng Khởi khi có ảnh đúng giấy phép (tự chụp, hoặc ảnh Wikimedia Commons đã kiểm trang mô tả) | Đặt ảnh Commons ngay (mất thêm ≈ 0,1 ngày kiểm giấy phép, ghi công trong `CREDITS.md`) |
| U-D3 | Nội dung landing | **Dùng bản nháp ở [landing-page-plan.md](../landing-page-plan.md) mục 3** (hero, 5 bước, 3 thẻ, chân trang) | Bạn sửa chữ |
| U-D4 | Hội thoại mẫu tĩnh (`ChatDemo`, ca `K04`) | **Bỏ ở lượt này** (plan gốc cũng ghi "làm nếu còn dư") | Làm, thêm ≈ 0,1 ngày |
| U-D5 | Trang đăng nhập | **Viết lại bằng Tailwind theo token hiện có**, chỉ mượn bố cục hai cột và hành vi của Ralion; **không thêm `@primer/octicons-react`** (dùng hai biểu tượng SVG nhúng) | Chép nguyên CSS module 738 dòng của Ralion rồi thay hex |
| U-D6 | Kiểm giao diện | **Vitest + kiểm tay ở 375 px và 1280 px + Lighthouse của Chrome**; Playwright dời sang Phase 9 (chưa có trong `package.json`) | Cài Playwright ngay (thêm ≈ 0,3 ngày) |

**Về backend**: giữ nguyên D1–D8 ở [phase-2.md](phase-2.md) mục 3 (Modal riêng, khóa DeepSeek riêng, `underthesea` với đường lui âm tiết, CLI thay upload, kiểm quote trên parent, đếm token xấp xỉ, `POST /api/v1/chat/ask` không stream, làm bằng giả nếu chưa có khóa). Nếu bạn chưa trả lời, tôi dùng mặc định.

**Về CP-2A** (từ [bao-cao-phase-2.md](bao-cao-phase-2.md) mục 5): khóa ngoại `team_members` đang là `RESTRICT`; nói tôi nếu muốn `CASCADE`.

## 3. Luồng UI

Cấu trúc hiện có (Phase 1): `frontend/src/app/[locale]/page.tsx` (trang khung), `login/page.tsx` (trang khung), Tailwind v4 với token (`bg-accent`, `text-ink`, `text-ink-2`, `border`…), `messages/vi.json` (khối `home`, `login`), `Link` từ `@/i18n/navigation`, Vitest + React Testing Library. **Không thêm phụ thuộc mới.**

### U1. Landing page (≈ 0,5 ngày)

Theo [landing-page-plan.md](../landing-page-plan.md), điều chỉnh cho khớp cấu trúc hiện có.

**Tệp:**

```text
frontend/src/app/[locale]/page.tsx          → thay trang khung: ghép các phần bên dưới (giữ đường dẫn, không tạo nhóm (marketing))
frontend/src/features/landing/
  Navbar.tsx  Hero.tsx  Steps.tsx  FeatureCards.tsx  Footer.tsx
  landing.test.tsx
frontend/messages/vi.json                   → thay khối `home` bằng khối `landing`
```

**Việc:**
1. **Navbar:** chữ "VSF Onboarding Assistant", hai liên kết neo (**Cách hoạt động**, **Tính năng**), nút **Đăng nhập** → `/vi/login`; liên kết "Bỏ qua tới nội dung" đầu trang.
2. **Hero:** nhãn "Trợ lý onboarding cho nhân sự mới", tiêu đề "Mới vào công ty, hỏi là biết bước tiếp theo", mô tả, nút chính **Bắt đầu hỏi** → `/vi/login`, nút phụ **Xem cách hoạt động** cuộn tới mục 5 bước, ghi chú "Đăng nhập bằng email công ty". Khung ảnh: nền gradient bằng token (U-D2); tiêu đề **không** nêu tên công ty như trang chính thức.
3. **Steps:** 5 bước đánh số (đặt câu hỏi, tìm trong tài liệu đã duyệt, trả lời có trích dẫn hoặc chỉ đúng quy trình, hỏi lại khi thiếu điều kiện, tạo ticket khi cần).
4. **FeatureCards:** ba thẻ (Có nguồn dẫn chứng, Không đoán, Link và form đã duyệt).
5. **Footer:** "VSF Onboarding Assistant — Bản demo thực tập, chưa phải sản phẩm chính thức", liên hệ demo dạng `…@vsf-demo.example`, bản quyền; dòng ghi công ảnh chỉ khi có ảnh.
6. Chữ nằm hết trong `messages/vi.json` (khối `landing`); component là thuần trình bày (`useTranslations`), trang tĩnh, không gọi API; `generateMetadata` giữ `title`/`description` sẵn có.
7. Kỹ thuật: cột giữa, một cột trên điện thoại, lề 16 px; chuyển động nhẹ bằng CSS, tắt khi `prefers-reduced-motion`; thẻ ngữ nghĩa (`header`, `main`, `section`, `footer`), tương phản đạt chuẩn ở cả chế độ sáng và tối (token đã có cả hai).

**Test (Vitest):** mỗi phần render đúng chữ từ `vi.json`; nút "Bắt đầu hỏi" và "Đăng nhập" trỏ `/vi/login`; liên kết neo có đích tồn tại; quét `features/landing` không có chuỗi tiếng Việt cứng ngoài `vi.json`; cập nhật `src/app/[locale]/page.test.tsx` và `src/i18n/messages.test.ts` cho khối `landing`.

**Cổng:** `npm run lint`, `typecheck`, `test`, `build` xanh; tay ở 375 và 1280 px không tràn ngang; Lighthouse di động ≥ 90 hiệu năng và khả năng truy cập; không có chữ VLearn/VinUni, không số liệu chưa đo, không câu nào ngụ ý VSF làm việc ở Vincom.

### U2. Trang đăng nhập — vỏ giao diện (≈ 0,4 ngày)

Mục tiêu: có giao diện và hành vi đúng để Phase 4 chỉ cần viết backend xác thực. **Chưa** đăng nhập được thật.

**Tệp:**

```text
frontend/src/app/[locale]/login/page.tsx     → trang (server) bọc LoginForm
frontend/src/features/auth/LoginForm.tsx     → form (client component)
frontend/src/features/auth/routing.ts        → internalPath, resolvePostLoginPath (hàm thuần)
frontend/src/features/auth/session.ts        → authApi.login, lớp lỗi SessionError (gọi /api/v1/auth/login)
frontend/src/features/auth/*.test.ts(x)
frontend/messages/vi.json                    → khối `login`
```

**Việc** (mượn hành vi từ `frontend/src/app/login/page.tsx` và `features/auth/routing.ts` của Ralion, viết lại bằng Tailwind):
1. **Bố cục hai cột:** panel trái (gradient theo token, ba nguyên tắc: có nguồn dẫn chứng, không đoán dữ liệu cá nhân, chỉ dùng link đã duyệt) và thẻ form bên phải; dưới 980 px xếp một cột, dưới 680 px ẩn panel trái. Header chỉ có thương hiệu và nhãn "Bản demo thực tập" (chưa có logo Vin/VSF).
2. **Form:** ô email và mật khẩu có biểu tượng SVG nhúng; `autoComplete="username"` và `"current-password"`; đọc giá trị từ `FormData` để trình quản lý mật khẩu điền tự động vẫn hoạt động; kiểm email ở client, mật khẩu chỉ cần không rỗng (chính sách độ dài do server quyết); nút gửi có spinner; hộp lỗi `role="alert"`; chuyển động `reveal` tắt khi `prefers-reduced-motion`.
3. **`internalPath`:** chỉ nhận đường dẫn nội bộ cho tham số `?next=`, loại `//evil.com`, `/\evil.com`, `https://evil.com`, `javascript:`.
4. **`resolvePostLoginPath`:** nhân viên → `/chat`; HR, Owner, Admin → khu quản trị (tên route chốt ở Phase 8); `?next=` chỉ nhận nếu hợp lệ với vai trò. Là hàm thuần, có test ngay; chuyển hướng thật chỉ chạy khi backend đăng nhập có (Phase 4).
5. **`authApi.login`:** `fetch` `POST /api/v1/auth/login` với `credentials: "include"`. Backend chưa có route này nên trang hiện lỗi chung "Không thể đăng nhập lúc này, thử lại sau"; **đây là hành vi đúng của vỏ**, và ghi rõ trong báo cáo.
6. **Không chép:** `authHeaders()`/`X-User-Id`, `localStorage["ralion-demo-user-id"]`, video demo và `iframe`, `LanguageSwitcher`, khối tài khoản test trỏ Google Doc, các nhánh `MUST_CHANGE_PASSWORD`/`NO_ACTIVE_PROJECT`/`/select-project`, "Quên mật khẩu", "Tạo tài khoản".

**Test (Vitest):** email sai hiện lỗi; mật khẩu rỗng bị chặn; lỗi từ server hiện đúng chỗ; nút chuyển sang trạng thái đang gửi; các giá trị `?next=` độc hại đều rơi về trang mặc định; chuyển trang đúng theo vai trò (hàm thuần); quét mã không có hex cứng (`#[0-9a-f]{3,8}` ngoài `globals.css`), không có `ralion`, `X-User-Id`, `LanguageSwitcher`.

**Cổng:** lint, typecheck, test, build xanh; tay ở 375 và 1280 px; đổi sáng/tối không vỡ; `grep` sạch các chuỗi cấm.

**CP-U1:** bạn chạy `npm run dev` (hoặc dùng `docker compose up` cho backend rồi `npm run dev` cho frontend) và xem `http://127.0.0.1:3000/vi` và `/vi/login`; tôi chụp ảnh 375/1280 px kèm báo cáo.

### U3. Trang chat giả (≈ 0,2 ngày, phần giao diện của 2-E)

**Tệp:**

```text
frontend/src/app/[locale]/chat/page.tsx        → chỉ bật ngoài production (production trả 404)
frontend/src/features/chat/ChatPanel.tsx       → ô nhập, danh sách tin, khối "Nguồn"
frontend/src/features/chat/api.ts              → ask(question): gọi /api/v1/chat/ask; chế độ giả khi CHAT_API_MODE=mock
frontend/src/features/chat/*.test.tsx
```

**Việc:** ô nhập, nút gửi, câu trả lời kèm **khối "Nguồn"** (trích dẫn, tên tài liệu, phiên bản, mục), trạng thái đang tải, lỗi và "chưa có căn cứ"; chữ trong `vi.json`; chế độ `mock` trả dữ liệu mẫu (ví dụ câu trả lời "12 ngày" kèm nguồn D03b và một câu "chưa có căn cứ") để bạn thấy giao diện trước khi có backend thật; chuyển sang `live` ở 2-E.

**Test:** gửi câu hỏi và hiện câu trả lời kèm nguồn; hiện lỗi; hiện "chưa có căn cứ"; production không bật trang.

## 4. Luồng backend

Tham chiếu chi tiết cho từng bước là [phase-2.md](phase-2.md) mục 5; dưới đây là danh sách tệp, việc cụ thể và bằng chứng cho checkpoint.

**Cấu hình thêm** (`backend/src/config.py`, `.env.example` đã có tên biến): `embedding_provider` (`modal-bge-m3` | `fake`), `embedding_endpoint`, `embedding_api_key`, `llm_base_url`, `llm_api_key`, `llm_model`. Khóa là `SecretStr`, không log. **Phụ thuộc thêm** (`requirements.txt`): `httpx`, `markitdown[docx,pdf]`, `underthesea` (D3; kiểm dung lượng image và cài đặt trên Windows/CI, nếu nặng thì lùi về tách âm tiết).

### 2-B. Nạp tài liệu (≈ 0,75 ngày) → CP-2B

```text
backend/src/infrastructure/ai/
  embedding_port.py            Protocol: model_version, dimension, async embed(texts) → vectors
  fake_embedding.py            vector 1024 chiều xác định từ hash của văn bản, đã chuẩn hóa
  modal_embedding_adapter.py   httpx, lô ≤ 32, retry có giới hạn, kiểm model_version và dimension == 1024
  embedding_factory.py         chọn adapter theo EMBEDDING_PROVIDER
backend/src/services/ingest/
  parsing.py                   MarkItDown → Markdown, làm sạch (NFC, bỏ header/footer lặp), checksum
  quality_gate.py              không rỗng, có ≥ 1 section và ≥ 1 chunk, cảnh báo nghi ngờ bảng
  sectioning.py                parent theo heading H1–H3; dự phòng chia đoạn
  chunking.py                  child ≈ 256 token, giữ nguyên bảng và danh sách đánh số
  tokenizing.py                tách từ tiếng Việt cho lexical_text (D3)
  ingest_service.py            điều phối và ghi DB trong một transaction, idempotent
backend/src/cli/ingest_file.py python -m src.cli.ingest_file --id D03b
```

**Việc cụ thể:**
1. `ingest_file --id D03b` đọc dòng `D03b` trong `docs/chatbot-vsf/data/manifests/documents_manifest.csv` để lấy `title`, `version_label=2.0`, `effective_from=2024-01-01`, danh mục `nghi-phep`, `source_key`; đường dẫn file theo `relative_path`.
2. Tạo dữ liệu nền nếu chưa có: danh mục `nghi-phep` (từ `registry/document_categories.json`) và một user chủ sở hữu vai trò `HR` (từ `registry/users.json`); **mật khẩu dev không đưa vào mã**, băm khi tạo (hàm băm tạm; Phase 4 dùng hàm băm chính thức).
3. Ghi `documents`, `document_versions` (`ACTIVE`), `document_sections`, `document_chunks` (kèm `embedding`, `embedding_model_version`) và một dòng `audit_logs`.
4. Nạp lần hai cùng `content_checksum`: **bỏ qua, không nhân đôi**; cùng nhãn phiên bản mà nội dung khác: từ chối (INV5).

**Test:** đơn vị cho chunker (mục ngắn, bảng, danh sách đánh số, mục dài, không heading, không bao giờ 0 chunk), tách từ, checksum, `FakeEmbedding` xác định; tích hợp trên DB thật: nạp D03b bằng embedding giả, mọi chunk thuộc đúng một section cùng phiên bản (INV14), nạp lần hai idempotent.

**Bằng chứng CP-2B:** bảng đếm section/chunk/embedding cho D03b; ba chunk mẫu (tiêu đề, nội dung, `lexical_text`); kết quả kiểm tra bảng biểu (MarkItDown có giữ bảng của D03b không); thời gian nạp; giờ công.

### 2-C. Tìm kiếm hybrid (≈ 0,5 ngày) → CP-2C

```text
backend/src/services/retrieval/
  rrf.py                       reciprocal_rank_fusion(k=60), thuần, dễ test
  hybrid_search.py             dense top 30 + BM25 top 30 + lọc hiệu lực as_of + gộp parent + giới hạn token
  models.py                    RetrievedContext {chunk_id, section_id, heading, content, page, score}
```

**Việc cụ thể:**
0. **Spike 30 phút trước khi viết mã:** thử cú pháp truy vấn BM25 của `pg_search 0.25.4` trên đúng image bằng `psql` (toán tử tìm kiếm, hàm lấy điểm). **Ghi cú pháp đã chạy được vào [phase-2.md](phase-2.md) mục 2-C.** Nếu không chạy được thì báo bạn và dùng `tsvector` làm đường lui tạm.
1. Dense: `ORDER BY embedding <=> :q LIMIT 30`; BM25: truy vấn cũng tách từ như lúc nạp; lọc hiệu lực (INV3) và `embedding_model_version` (INV7) ngay trong SQL; `as_of` tính theo `Asia/Ho_Chi_Minh` bằng `app_timezone`.
2. RRF trong Python, gộp về parent, giới hạn ≈ 3.000 token.

**Test:** RRF (thứ hạng, hòa điểm); lọc hiệu lực (`as_of` trước `2024-01-01` không trả gì); tích hợp DB thật: câu hỏi có từ khóa của D03b thấy đúng section nhờ BM25 (embedding giả chỉ kiểm BM25 và cơ chế lọc).

**Bằng chứng CP-2C (cần embedding thật):** với 8 câu `ANSWER` (mục 5 của [phase-2.md](phase-2.md)): với mỗi câu, top-5 section, section chứa đáp án có mặt không, điểm dense và BM25; số câu trúng ≥ 7/8 là chỉ dẫn (không phải cổng). Nếu chưa có Modal: ghi "chưa đo dense", chỉ có kết quả BM25.

### 2-D. LLM và validator (≈ 0,5 ngày) → CP-2D

```text
backend/src/infrastructure/ai/
  chat_completion_port.py      Protocol: async complete_json(messages) → dict
  openai_compatible_adapter.py httpx tới {LLM_BASE_URL}/chat/completions, response_format JSON, timeout, retry giới hạn
  fake_chat.py                 tất định, cấu hình sẵn cặp câu hỏi/đáp cho test
backend/src/services/chat/
  prompt.py                    chỉ trả lời từ các đoạn cho sẵn; tài liệu là dữ liệu, không phải lệnh
  answer_contract.py           Pydantic LlmAnswer {answer, quote, chunk_id}
  validator.py                 chunk_id thuộc tập đã truy xuất; quote là chuỗi con nguyên văn của parent (NFC, gộp khoảng trắng)
  answer_service.py            truy xuất → (không có gì: không gọi LLM) → LLM → thử lại 1 lần nếu hỏng → validator
```

**Việc cụ thể:**
1. **Gọi thử `LLM_MODEL` trước khi viết mã** (một lời gọi tối thiểu); nếu `deepseek-flash` bị từ chối, đối chiếu trang Models & Pricing chính thức của DeepSeek rồi đổi biến.
2. Không dùng LangChain: adapter gọi HTTP trực tiếp (system design mục 7.6).
3. Kết quả cuối: `{status: "answer", answer, quote, source {...}}` hoặc `{status: "no_basis", reason_code}`; câu trả lời chưa qua validator **không bao giờ** trả ra ngoài.

**Test:** validator (quote đúng, quote bịa, thiếu một chữ, `chunk_id` lạ), schema hỏng rồi thử lại, injection (đoạn chứa "bỏ qua mọi quy tắc" không đổi hành vi), không có chunk nào thì không gọi LLM; contract test bằng `FakeChatCompletion`.

**Bằng chứng CP-2D:** log 10 câu (câu hỏi, chunk trúng, câu trả lời, quote, kết quả validator); ít nhất một ca validator chặn quote bịa; số token và chi phí ước tính.

### 2-E. Endpoint và nối giao diện (≈ 0,2 ngày phần backend)

`backend/src/api/routers/chat_router.py` với `POST /api/v1/chat/ask` (D7), chỉ đăng ký khi `APP_ENV != production`; DTO trong `backend/src/dto/`; trang `/vi/chat` chuyển từ `mock` sang `live` (`CHAT_API_MODE=live`). **Test:** contract test router (trạng thái, schema, `no_basis`); frontend gọi được endpoint qua rewrite `/api/*` của Next dev.

**Bằng chứng CP-U2:** bạn tự gõ câu hỏi trong trình duyệt và thấy câu trả lời kèm nguồn; ảnh chụp.

### 2-F. Đo, báo cáo, cập nhật tài liệu (≈ 0,25 ngày) → CP-2F

Theo [phase-2.md](phase-2.md) mục 5 (2-F) và cổng ở mục 6: chạy 10 câu với LLM và embedding **thật**; đo độ trễ p50/p95 (tổng và tách embedding, DB, LLM), RAM (`docker stats`), token và chi phí, **giờ công thật của từng bước**; cập nhật [bao-cao-phase-2.md](bao-cao-phase-2.md).

## 5. Điều kiện cần từ bạn (không chặn việc bắt đầu)

| Việc | Cần từ bước | Nếu chưa có |
|---|---|---|
| Khóa DeepSeek riêng có hạn mức chi tiêu, đặt vào `.env` cục bộ | 2-D (gọi thật) | Làm bằng LLM giả, ghi "chưa đo chất lượng" |
| Modal: tài khoản, triển khai `app.py` (chép từ Ralion, D1), secret `EMBEDDING_API_KEY`, budget; điền `EMBEDDING_ENDPOINT`, `EMBEDDING_API_KEY` vào `.env` | 2-B (nạp thật) và CP-2C | Làm bằng embedding giả; CP-2C chỉ có BM25 |
| Ảnh Vincom (nếu muốn) | U1 | Dùng gradient (U-D2) |
| Docker Desktop bật khi chạy test tích hợp | Mỗi bước backend | |

Không gửi khóa qua chat. Tôi không cần thấy khóa: tôi chỉ đọc biến môi trường trong mã.

## 6. Cập nhật tài liệu sau khi xong

- `master-plan.md` và `plan/README.md`: ghi rõ **landing (Phase 10)** và **giao diện đăng nhập (một phần Phase 4)** đã làm sớm; Phase 4 còn lại backend xác thực và nối API; Phase 10 còn lại ảnh (nếu chưa có) và hội thoại mẫu; cập nhật ước lượng theo giờ công thật.
- `landing-page-plan.md` và `frontend-login-reuse.md`: đổi trạng thái đầu tệp sang "đã thực hiện (vỏ)", ghi sai lệch.
- `README.md` gốc: cách nạp tài liệu và thử chat.
- `.env.example`: nếu thêm biến mới.

## 7. Rủi ro

| Rủi ro | Xử lý |
|---|---|
| Landing và đăng nhập ngốn thời gian, đẩy lùi lõi chatbot | Giới hạn cứng: U1 + U2 ≤ 1 ngày; quá thì dừng ở Hero + Footer và trang đăng nhập cơ bản; lõi (2-B đến 2-D) không bị cắt |
| Giao diện đăng nhập làm sớm lệch với backend Phase 4 | Chỉ khóa hợp đồng ở `authApi.login` (`POST /api/v1/auth/login`, cookie phiên); backend theo đúng hợp đồng này ở Phase 4 |
| Bị hiểu là trang chính thức của Vin/VSF | Không logo, nhãn "Bản demo thực tập", tiêu đề không nêu tên công ty |
| `underthesea` nặng hoặc lỗi | Lùi về tách âm tiết (D3) |
| Cú pháp BM25 khác kỳ vọng | Spike ở đầu 2-C, đường lui `tsvector` |
| Chưa có khóa thật khi tới CP-2C/2-D | Làm bằng giả, ghi "chưa đo"; không tuyên bố đạt cổng chất lượng |
| Sửa `0001_core` sau khi đã lên môi trường thật | Xem CP-2A; chốt trước khi đẩy `main` |
