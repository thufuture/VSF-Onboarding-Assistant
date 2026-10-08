# Embedding BGE-M3 tự host (chạy cùng máy `vsf-aws`)

Dịch vụ `embedder` trong `deploy/aws/compose.aws.yml`. Backend gọi `http://embedder:8080/embed` qua mạng Docker riêng; **không có cổng nào
được publish ra ngoài**. Hợp đồng `/embed` giống hệt Modal (`{"texts":[...]}` ≤ 32 chuỗi, header `Authorization: Bearer`, trả
`{"vectors","model_version","dimension"}`), nên backend chỉ cần đổi `EMBEDDING_ENDPOINT`.

## Thiết lập trên máy mới (một lần, ngoài repo)

1. Tạo `/opt/vsf-aws/env/embedder.env` (quyền 600, chủ sở hữu là người chạy deploy):
   ```
   EMBEDDING_API_KEY=<cùng giá trị với EMBEDDING_API_KEY trong backend.env>
   DTYPE=bf16
   HF_HUB_OFFLINE=1
   TORCH_THREADS=2
   ```
   - `DTYPE=bf16` chỉ nhanh trên CPU có AMX (họ m7i/c7i); CPU khác nên dùng `fp32`.
   - `HF_HUB_OFFLINE=1`: chạy hoàn toàn từ mô hình đã nạp sẵn trong ảnh, không gọi Hugging Face lúc khởi động.
2. Trong `backend.env`: `EMBEDDING_ENDPOINT=http://embedder:8080` (giữ nguyên `EMBEDDING_API_KEY`). Đổi xong phải
   `docker compose ... up -d --force-recreate backend` (`docker restart` không đọc lại env).
3. `scripts/aws/deploy.sh` tự build ảnh `vsf-embedder:bge-m3` (lần đầu mất vài phút, ~9 GB đĩa) và bật service; ảnh được gắn nhãn
   `vsf.embedder.src` là băm của `Dockerfile`, `requirements.txt`, `server.py`, đổi các file này thì deploy tự build lại.

## Giới hạn tài nguyên (vì sao)

`cpus: 1.5` và `mem_limit: 3500m`: máy chỉ có 2 vCPU/8 GiB và còn chạy Postgres + backend. Đo thật: lô 32 đoạn dài ~30 giây,
đỉnh RAM mô hình ~1,7 GB, `/api/v1/ready` của backend vẫn p95 26 ms khi embedder chạy hết công suất. Câu hỏi đơn lẻ ~0,12 giây.

## Kiểm tra nhanh

```
docker compose --env-file /opt/vsf-aws/env/compose.env -f /opt/vsf-aws/deploy/aws/compose.aws.yml ps embedder
docker compose ... logs --tail 5 embedder      # dòng "[embedder] BAAI/bge-m3@<mã bản> · cpu · bf16 ..."
```

`model_version` PHẢI giữ nguyên dạng `BAAI/bge-m3@5617a9f6…`: cơ sở dữ liệu lưu đúng chuỗi này và truy hồi lọc theo nó; đổi chuỗi thì
tìm kiếm trả rỗng cho tài liệu đã nạp.

## Quay lại

Đặt lại `EMBEDDING_ENDPOINT` về nơi cũ (máy embedder riêng hoặc Modal) trong `backend.env`, rồi `up -d --force-recreate backend`.
