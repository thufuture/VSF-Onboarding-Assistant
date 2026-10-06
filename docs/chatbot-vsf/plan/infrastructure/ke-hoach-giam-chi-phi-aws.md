# Kế hoạch giảm chi phí AWS

> Cập nhật 25/09/2026. Bối cảnh: [bao-cao-trien-khai-aws-vercel.md](bao-cao-trien-khai-aws-vercel.md) và
> [huong-dan-kiem-tra-ha-tang-aws.md](huong-dan-kiem-tra-ha-tang-aws.md). Giá dưới đây là **ước tính** từ số đo thật trên
> Console và giá công khai; hãy đối chiếu lại ở Billing → Cost Explorer trước khi quyết định.

## 0. Kết luận nhanh

- **$4,11 không phải chi phí một ngày.** Đó là tổng cộng dồn từ khi máy chủ chạy (23/09) tới hôm nay trong tháng 9.
- **Nhưng tốc độ tiêu thật sự là khoảng $2,4–3/ngày (~$75–80/tháng) nếu máy chạy 24/7.** Credit còn $115,89 sẽ hết
  sau khoảng **45 ngày** (giữa tháng 11/2026), sớm hơn nhiều so với hạn 22/03/2027 (180 ngày).
- **Đính chính:** các tài liệu trước ghi "chi phí ~1 USD/tháng" và "$0 khi Eligible for the free offer" là **sai**. Đó chỉ là số
  của ngày đầu chạy chưa đủ 24 giờ. "Free tier eligible" chỉ có nghĩa không bị tính phí vượt mức ngoài credit; mọi giờ chạy vẫn **trừ vào credit**.
- **Cách giảm hiệu quả nhất, không rủi ro, có thể đảo ngược:** tắt EC2 khi không dùng (chỉ trả ổ đĩa và IP, ~$6/tháng), và bật lại khi cần. Có thể kết hợp hạ cấu hình máy.

## 1. Chi phí thực tế (đọc từ Console, tháng 9/2026)

| Khoản | Số tiền tới 25/09 | Nguyên nhân |
|---|---|---|
| EC2 - Compute | $3,81 | Giờ chạy máy `m7i-flex.large` (2 vCPU, 8 GB). Đo được ≈ **$0,10/giờ** |
| Virtual Private Cloud | $0,17 | Phí IPv4 công khai (Elastic IP), $0,005/giờ ≈ $3,7/tháng |
| EC2 - Other | $0,13 | Ổ EBS 30 GB gp3 ≈ $2,4/tháng |
| S3, Secrets Manager | $0,00 | Không thuộc dự án, chi phí bằng 0 |
| **Tổng** | **$4,11** | Credit còn **$115,89** / 180 ngày |

Máy chạy liên tục nên **giờ chạy EC2 chiếm ~93% chi phí**. Ổ đĩa và IP là khoản cố định nhỏ (~$6/tháng) và vẫn bị tính khi máy tắt.

## 2. Ngân sách credit

Hạn dùng còn 180 ngày. Để credit đủ tới hạn, mức chi tối đa khoảng **$115,89 / 6 tháng ≈ $19/tháng**.

| Kịch bản | Ước tính/tháng | Credit đủ dùng | Đạt hạn 22/03/2027? |
|---|---|---|---|
| Chạy 24/7 `m7i-flex.large` (hiện tại) | ~$79 | ~44 ngày | Không |
| Chạy 12 giờ/ngày | ~$42 | ~83 ngày | Không |
| Chạy 8 giờ/ngày ngày thường (~176 giờ) | ~$24 | ~145 ngày | Gần đủ |
| Chỉ bật khi demo (~20 giờ/tháng) | ~$8 | > 6 tháng | **Có** |
| Tắt hẳn (chỉ EBS + IPv4) | ~$6 | > 6 tháng | **Có** |
| `t3.medium` 24/7 (4 GB) | ~$45 | ~77 ngày | Không |
| `t3.small` 24/7 (2 GB) | ~$25 | ~137 ngày | Gần đủ |
| `t3.small` + tắt khi không dùng (8 giờ/ngày) | ~$11 | > 6 tháng | **Có** |

Giá `t3.small`/`t3.medium` là ước tính theo bảng giá công khai vùng Singapore, cần xác nhận trên AWS Pricing Calculator và
xem máy đó có được tính là "Free tier eligible" trong tài khoản Free Plan không (kiểm tra ở màn hình Launch instance).

## 3. Các phương án

| Phương án | Cách làm | Ưu điểm | Nhược điểm |
|---|---|---|---|
| **A. Tắt/bật EC2 theo nhu cầu** | Stop khi không dùng, Start khi demo | Giảm mạnh nhất; đảo ngược được; không đổi code | Web không trả lời khi máy tắt; deploy GitHub cần bật máy trước |
| **B. Hạ cấu hình máy** | Đổi `instance_type` sang `t3.medium`/`t3.small` bằng Terraform | Giảm 45–70% khi chạy 24/7 | Cần dừng máy vài phút; ít RAM hơn (hiện dùng ~0,9 GB/8 GB nên đủ) |
| **C. Kết hợp A + B** | Máy nhỏ, tắt khi không dùng | Rẻ nhất mà vẫn dùng được | Phải nhớ bật/tắt |
| **D. Xóa hẳn (`terraform destroy`)** | Xóa toàn bộ, dựng lại khi cần | Về $0 | **Mất DB** nếu không backup; dựng lại mất thời gian |

## 4. Khuyến nghị

1. **Ngay lập tức:** tắt EC2 khi không demo (phương án A). Không mất dữ liệu, không đổi IP, chỉ còn ~$6/tháng.
2. **Sau đó, nếu cần chạy thường xuyên:** hạ xuống `t3.medium` (phương án B), tắt/bật theo giờ làm việc.
3. **Không nên** `terraform destroy` khi chưa backup DB.

## 5. Hướng dẫn tắt và bật EC2

### 5.1 Trên AWS Console
1. Góc phải trên, chọn vùng **Asia Pacific (Singapore)**.
2. **EC2 → Instances**, tích chọn `vsf-aws`.
3. **Tắt:** **Instance state → Stop instance → Stop**. (Đừng chọn *Terminate*, sẽ **xóa máy và DB**.)
4. **Bật:** **Instance state → Start instance**. Đợi *Status check* thành 2/2 (khoảng 1–2 phút).

### 5.2 Bằng lệnh AWS CLI (nếu cần)
```
aws ec2 stop-instances  --region ap-southeast-1 --instance-ids i-001256d35e85809ae
aws ec2 start-instances --region ap-southeast-1 --instance-ids i-001256d35e85809ae
aws ec2 describe-instances --region ap-southeast-1 --instance-ids i-001256d35e85809ae --query "Reservations[0].Instances[0].State.Name" --output text
```
Policy `terraform-deployer` đã có quyền `StartInstances`/`StopInstances`.

### 5.3 Điều gì giữ nguyên, điều gì thay đổi
| Khi tắt máy | Kết quả |
|---|---|
| Dữ liệu DB, file trên ổ EBS | **Giữ nguyên** |
| IP `3.1.239.21` và tên miền DuckDNS | **Giữ nguyên** (Elastic IP vẫn gắn máy), không cần sửa DNS |
| Container backend/db/caddy | Tự chạy lại khi bật máy (đã đặt `restart: unless-stopped`) |
| Giao diện Vercel | Vẫn mở được, nhưng **đăng nhập và chat báo lỗi** vì backend không chạy |
| Chi phí | Không tính giờ EC2; vẫn tính EBS (~$2,4) và IPv4 (~$3,7) mỗi tháng |
| Lần hỏi đầu sau khi bật | Chậm hơn (Modal khởi động lạnh, có thể ~1 phút) |

### 5.4 Kiểm tra sau khi bật
1. Mở `https://vsf-assistant.duckdns.org/api/v1/health` → `{"status":"ok"}` (nếu chưa lên, đợi thêm 1 phút).
2. Mở `https://vsf-onboarding-assistant.vercel.app`, đăng nhập và hỏi thử một câu.
3. Nếu health không lên sau 5 phút: vào EC2 Instance Connect (xem hướng dẫn kiểm tra hạ tầng), chạy `sudo docker ps`.

## 6. Hạ cấu hình máy bằng Terraform (phương án B)

1. Trong `infra/aws/terraform.tfvars` (không nằm trong git), thêm: `instance_type = "t3.medium"`.
2. Chạy `terraform plan`: phải chỉ thấy **1 thay đổi tại chỗ** (`aws_instance.vsf` đổi `instance_type`); nếu thấy "must be replaced" thì **dừng lại**, không apply.
3. `terraform apply`: Terraform tự dừng máy, đổi cấu hình, bật lại (mất kết nối vài phút). Dữ liệu trên EBS giữ nguyên.
4. Kiểm tra như mục 5.4 và theo dõi RAM bằng `free -h` (hiện ~0,9 GB đang dùng; nếu thường xuyên trên 80% thì tăng cấu hình lại).
5. `t3.small` (2 GB) rẻ hơn nhưng dễ thiếu RAM khi DB và backend cùng tải; nên thử `t3.medium` trước.

## 7. Theo dõi chi phí

- **Console → Billing → Credits:** xem "Credits remaining" mỗi vài ngày; đối chiếu với bảng mục 2.
- **Billing → Budgets:** tạo cảnh báo email khi chi tiêu trong tháng vượt $15–20.
- **Cost Explorer:** nhóm theo *Service* để xem EC2 Compute chiếm bao nhiêu.
- Modal (embedding) tính riêng; app tự về 0 khi không có yêu cầu, xem Modal → Credits.

## 8. Lưu ý vận hành

- **Trước buổi demo/báo cáo với mentor:** bật máy trước 10 phút và hỏi thử một câu để "làm nóng".
- **Khi merge code lên `main`:** job deploy cần SSH vào EC2, nên phải **bật máy trước**, nếu máy đang tắt thì deploy thất bại. Deploy xong có thể tắt lại.
- **Mở SSH tạm cho IP của bạn** chỉ khi cần, xóa sau khi xong (xem hướng dẫn kiểm tra hạ tầng).
- **Nếu credit sắp hết** mà chưa hết hạn: tắt máy, hoặc `terraform destroy` sau khi backup DB bằng `scripts/vps/backup-db.sh`.
