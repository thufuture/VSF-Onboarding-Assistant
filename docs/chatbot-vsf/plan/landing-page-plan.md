# Phase 10 — Landing page tiếng Việt, tối giản (0,5 ngày công)

> Trạng thái: **bản nháp v4 để duyệt** (rút còn 0,5 ngày để nhường chỗ cho triển khai). Thuộc [master-plan.md](master-plan.md), **Phase 10 [Stretch]** (tuần 4, ≈ 0,5 ngày công). Làm **sau khi chatbot lõi đã chạy**; nếu trễ thì đây là thứ đầu tiên bị cắt, và Phase 12 (nghiệm thu) **không phụ thuộc** vào phase này. Trước khi phase này xong, `/vi` chuyển hướng tới `/vi/login` (chưa đăng nhập) hoặc `/vi/chat`.
> Nguồn bố cục: https://vlearn.dev/welcome (đã đọc cấu trúc). **Chỉ mượn bố cục**, không mượn chữ, ảnh, logo, minh họa của VLearn/VinUni.

## 1. Mục tiêu và phạm vi

**Mục tiêu.** Một trang công khai để người mới hiểu trong vài giây trợ lý này làm gì và bấm vào đâu để bắt đầu.

**Trong phạm vi**
- Một trang, **chỉ tiếng Việt** (`/vi`). Chữ nằm trong `messages/vi.json`, cấu trúc sẵn cho `en` nhưng không làm `en` trong MVP.
- Nút "Bắt đầu hỏi" dẫn tới `/vi/login` (trang đăng nhập đã làm ở Phase 4, xem [frontend-login-reuse.md](frontend-login-reuse.md)).
- Một ảnh minh họa Vincom Center Đồng Khởi, có giấy phép và chú thích.

**Ngoài phạm vi**
- Công tắc ngôn ngữ, bản dịch `en`, kiểm khớp khóa dịch, `hreflang`, Open Graph đa ngữ.
- Khối ba con số, hành trình ba giai đoạn (đã bỏ so với bản trước để giữ ≈ 0,5 ngày).
- Số liệu hiệu quả chưa đo, nhận xét/đánh giá giả, icon mạng xã hội giả.
- Không trình bày nội dung bộ seed như chính sách thật của VSF.

## 2. Đối chiếu với VLearn (chỉ bố cục)

| # | Phần ở VLearn | Phiên bản của dự án |
|---|---|---|
| 1 | Thanh điều hướng | Chữ "VSF Onboarding Assistant", hai liên kết neo (**Cách hoạt động**, **Tính năng**), nút **Đăng nhập** |
| 2 | Hero: tiêu đề, mô tả, nút chính + phụ, ghi chú đăng nhập | Tiêu đề về giá trị; **Bắt đầu hỏi** và **Xem cách hoạt động**; ghi chú đăng nhập |
| 3 | Quy trình 5 bước đánh số | Năm bước của trợ lý |
| 4 | Hội thoại mẫu | Một hội thoại tĩnh lấy từ ca golden `K04` (**làm nếu còn thời gian**) |
| 5 | Ba thẻ tính năng | Có nguồn · Không đoán · Link và form đã duyệt |
| 6 | Chân trang | Thương hiệu + nhãn "Bản demo thực tập", liên hệ demo, bản quyền, ghi công ảnh |

## 3. Nội dung (bản nháp tiếng Việt, chốt cùng bạn trước khi làm)

### 3.1 Hero
- Nhãn nhỏ: **Trợ lý onboarding cho nhân sự mới**
- Tiêu đề: **Mới vào công ty, hỏi là biết bước tiếp theo**
- Mô tả: *Trợ lý trả lời từ tài liệu đã được duyệt, chỉ đúng quy trình và đúng đầu mối. Điều gì chưa có nguồn, trợ lý nói thẳng là chưa có, thay vì đoán.*
- Nút chính: **Bắt đầu hỏi** → `/vi/login`; nút phụ: **Xem cách hoạt động** → cuộn tới mục 3.2
- Ghi chú: *Đăng nhập bằng email công ty.*

Tiêu đề cố ý **không** nêu tên công ty như thể đây là trang chính thức của VSF/Vingroup.

### 3.2 Năm bước
1. **Đặt câu hỏi.** Hỏi như nhắn cho đồng nghiệp: "Nghỉ phép năm được mấy ngày?"
2. **Tìm trong tài liệu đã duyệt.** Chỉ dùng tài liệu còn hiệu lực tại ngày bạn hỏi.
3. **Trả lời có trích dẫn, hoặc chỉ đúng quy trình.** Kèm nguồn để bạn tự kiểm tra.
4. **Hỏi lại khi thiếu điều kiện.** Ví dụ cần biết bạn thuộc đơn vị nào rồi mới trả lời chính xác.
5. **Tạo ticket khi cần.** Bản nháp hiện ra cho bạn xem; chỉ gửi sau khi bạn xác nhận.

### 3.3 Hội thoại mẫu (tĩnh, lấy từ ca golden `K04`)
Cả hai lượt có trong bộ câu hỏi vàng và tài liệu nguồn có trong bộ seed, nên không bịa:

- Bạn: *Máy công ty của tôi dùng hệ điều hành gì?*
- Trợ lý (hỏi làm rõ): *Câu trả lời phụ thuộc đơn vị của bạn. Bạn thuộc đơn vị nào?*
- Bạn: *Tôi thuộc Vinmec.*
- Trợ lý (trả lời): *Máy cấp cho nhân sự thuộc Vinmec dùng Ubuntu 22.04 LTS.* Nguồn: *Quy trình cấp phát thiết bị*.

Hiển thị nhãn **"Hội thoại minh họa"**; nội dung dựa trên tài liệu giả lập. Sau Phase 7, có thể thay bằng bản ghi thật của bot, đối chiếu lại với `K04` (câu trả lời phải chứa "Ubuntu 22.04 LTS").

### 3.4 Ba thẻ tính năng
- **Có nguồn dẫn chứng.** Mỗi câu trả lời kèm đoạn trích và tên tài liệu, mở ra xem được.
- **Không đoán.** Chỗ ngồi, mentor, hợp đồng, thiết bị của riêng bạn: trợ lý chỉ cho bạn cách tra cứu đúng nơi, không tự nêu con số.
- **Link và form đã duyệt.** Chỉ đưa đường dẫn, đầu mối và biểu mẫu do bộ phận phụ trách duyệt và còn hiệu lực.

### 3.5 Chân trang
- Thương hiệu: **VSF Onboarding Assistant** — *Bản demo thực tập, chưa phải sản phẩm chính thức.*
- Liên hệ: một địa chỉ demo dạng `…@vsf-demo.example` (địa chỉ giả, khớp bộ seed); thay bằng địa chỉ thật sau khi mentor cấp.
- Bản quyền: "© 2026 VSF Onboarding Assistant. Bản demo thực tập."
- Ghi công ảnh: một dòng theo `CREDITS.md`, ví dụ "Ảnh minh họa: <tác giả>, <giấy phép>, qua Wikimedia Commons".

## 4. Ảnh Vincom Center Đồng Khởi (ảnh minh họa)

**Vai trò của ảnh.** Chỉ là **ảnh minh họa trang trí** cho hero. Trang **không** nêu và không ngụ ý rằng VSF làm việc ở tòa nhà này (thông tin đó chỉ có từ trang tuyển dụng bên thứ ba, chưa được VSF xác nhận; bộ seed cũng ghi đó là "địa điểm giả định"). Vì vậy:
- Chỉ **một** ảnh, đặt ở hero; không đặt ảnh ở phần hướng dẫn ngày đầu hay bất kỳ chỗ nào gắn với địa điểm làm việc.
- Chú thích hiển thị cạnh ảnh: **"Ảnh minh họa: Vincom Center Đồng Khởi, TP.HCM"**; `alt` mô tả đúng nội dung ảnh (tòa nhà), không nêu tên công ty.

**Nguyên tắc nguồn.** Không lấy ảnh từ Google Images, mạng xã hội hay trang tin (không rõ giấy phép); không hotlink; mỗi ảnh có nguồn và giấy phép ghi lại được.

**Thứ tự ưu tiên**
1. Ảnh do chính bạn chụp.
2. [Wikimedia Commons: Category Vincom Center Dong Khoi](https://commons.wikimedia.org/wiki/Category:Vincom_Center_Dong_Khoi): chỉ ảnh có giấy phép cho phép dùng lại. Đã thấy [một ảnh CC BY 2.0](https://commons.wikimedia.org/wiki/File:Vincom_Center,_Ciudad_de_Ho_Chi_Minh,_Vietnam_(36608916004).jpg) (ghi công tác giả, dẫn giấy phép, nêu nếu có chỉnh sửa); mỗi ảnh phải mở trang mô tả xem lại giấy phép và tác giả trước khi dùng; ảnh cũ nhập từ Panoramio cần xem kỹ.
3. Dự phòng: nền gradient theo token thiết kế, chừa khung ảnh để thay sau.

**Kỹ thuật ảnh.** `frontend/public/images/landing/`, WebP nhiều kích cỡ, `next/image` với `priority` cho hero; lớp phủ để chữ đạt tương phản ≥ 4,5:1. `CREDITS.md` mỗi ảnh một dòng: tệp, tác giả, giấy phép, đường dẫn trang nguồn, ngày lấy, có chỉnh sửa hay không.

## 5. Thương hiệu và pháp lý

- Không đặt logo Vingroup/VinSmart Future; không dùng màu/kiểu chữ nhận diện chính thức như thể đây là trang chính thức. Dùng chữ "VSF Onboarding Assistant" và nhãn "Bản demo thực tập".
- Chỉ dùng logo chính thức nếu mentor đồng ý bằng văn bản (câu hỏi mở số 3 của master-plan).
- Không nêu cam kết hoặc tuyên bố nhân danh công ty. Trang không nêu thông tin về VSF (văn phòng, quy mô, phúc lợi).
- Trang công khai: không nhúng dữ liệu nội bộ; không nhúng tracking bên thứ ba.

## 6. Thiết kế và kỹ thuật

- **Token**: dùng token của Phase 1; landing không định nghĩa màu mới. Chế độ sáng/tối theo token nếu Phase 1 đã có sẵn, không làm thêm.
- **Bố cục**: cột giữa, một cột ở điện thoại, lề 16px, khoảng trống rộng như VLearn.
- **Chuyển động**: rất nhẹ bằng CSS; tắt khi `prefers-reduced-motion`; không thêm thư viện.
- **Khả năng truy cập**: liên kết "Bỏ qua tới nội dung", thẻ ngữ nghĩa, tương phản đạt chuẩn, `lang="vi"`.
- **Cấu trúc tệp**

```
frontend/
  app/[locale]/(marketing)/page.tsx
  features/landing/  Navbar.tsx  Hero.tsx  Steps.tsx  FeatureCards.tsx  Footer.tsx  (ChatDemo.tsx nếu còn thời gian)
  messages/vi.json                       # khối `landing`
  public/images/landing/*.webp  CREDITS.md
```

- Mỗi phần là component thuần trình bày, nhận chữ từ `next-intl`; trang tĩnh (SSG), không gọi API; `generateMetadata` cho `title`/`description`.

## 7. Các việc (≈ 0,5 ngày công)

| # | Việc | Ước lượng |
|---|---|---|
| L1 | Chốt nội dung (mục 3) cùng bạn | 0,05 ngày |
| L2 | Chọn ảnh, kiểm giấy phép, xử lý WebP, viết `CREDITS.md` (nếu chưa có ảnh đạt: dùng nền gradient) | 0,1 ngày |
| L3 | Dựng trang: Navbar, Hero, Steps, FeatureCards, Footer | 0,25 ngày |
| L4 | Responsive, khả năng truy cập, chuyển động | 0,05 ngày |
| L5 | Kiểm thử và rà soát cuối | 0,05 ngày |

Cộng lại đúng 0,5 ngày và **rất sát**: nếu trễ, chỉ dựng Hero + nút + Footer (≈ 0,25 ngày), hoặc bỏ phase. Hội thoại mẫu (`ChatDemo`, ≈ 0,1 ngày) chỉ làm khi còn dư thời gian.

## 8. Kiểm chứng và cổng hoàn thành

| Kiểm | Cách | Đạt khi |
|---|---|---|
| Luồng nút | Playwright: bấm "Bắt đầu hỏi" | Tới `/vi/login` (có form, không phải 404); "Xem cách hoạt động" cuộn đúng mục |
| Không chữ cứng | Vitest/eslint quét `features/landing` tìm chuỗi tiếng Việt nằm ngoài `messages/vi.json` | Không có |
| Giao diện | Playwright chụp 375 và 1280 px | Không tràn ngang, không vỡ bố cục |
| Lighthouse | Cỡ di động và máy tính | Hiệu năng ≥ 90, khả năng truy cập ≥ 90 |
| Ảnh | Đối chiếu thư mục ảnh với `CREDITS.md` | Mỗi ảnh có một dòng; ghi công và chú thích "Ảnh minh họa" hiện trên trang |
| Nội dung | Đọc tay + `grep` | Không có số liệu chưa đo; không còn chữ VLearn/VinUni; không câu nào nói hay ngụ ý VSF làm việc ở Vincom Đồng Khởi |

## 9. Rủi ro và câu hỏi mở

| Rủi ro / câu hỏi | Xử lý |
|---|---|
| Giấy phép ảnh không rõ | Ưu tiên ảnh tự chụp; ảnh Commons kiểm từng trang; có phương án gradient |
| Sao chép quá sát VLearn | Chỉ giữ khung bố cục; chữ, ảnh, màu, minh họa đều là của mình |
| Bị hiểu là trang chính thức của Vin/VSF | Không logo, nhãn "Bản demo thực tập", ảnh chú thích "minh họa", tiêu đề không nêu tên công ty |
| Hội thoại mẫu lệch bot thật | Dùng ca golden có thật; đối chiếu lại sau Phase 7 |
| **Hỏi bạn:** giọng văn xưng "bạn" hay "em" như VLearn? | Chốt ở L1 |
