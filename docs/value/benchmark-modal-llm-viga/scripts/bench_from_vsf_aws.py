# -*- coding: utf-8 -*-
"""Đo độ trễ embedding ĐÚNG đường backend dùng: chạy trên máy chính vsf-aws, gọi máy embedder qua mạng riêng và gọi Modal.

Chỉ dùng thư viện chuẩn của Python 3 (máy Ubuntu có sẵn), không cài gì, không ghi gì vào hệ thống, không đụng DB.

    EMBEDDER_URL=http://172.31.26.137:8080 EMBEDDER_KEY=<khóa tự host> \
    MODAL_URL=<EMBEDDING_ENDPOINT> MODAL_KEY=<EMBEDDING_API_KEY> python3 bench_from_vsf_aws.py

Khóa không bao giờ được in ra. Mỗi câu gọi 5 lần, xen kẽ hai nguồn; lần đầu của mỗi nguồn bỏ đi (làm ấm).
"""

import json
import os
import statistics
import sys
import time
import urllib.request

QUESTIONS = [
    "Hồ sơ cần nộp trong ngày đầu gồm những gì?",
    "Nộp hồ sơ ngày đầu thì liên hệ đầu mối nào?",
    "Chương trình Đào tạo Hội nhập có bắt buộc không và điều kiện hoàn thành là gì?",
    "Bài test cuối khóa phải đạt bao nhiêu phần trăm?",
    "Khi nào tôi ký hợp đồng lao động?",
    "Đăng ký faceid chấm công ở đâu?",
    "Tôi nhận laptop ở đâu?",
    "Nhận laptop xong thì làm gì tiếp theo?",
    "Muốn dùng VPN hoặc xin exception USB thì cần ai đồng thuận?",
    "Tôi chưa có lý lịch tư pháp thì sao?",
]
REPEAT = 5


def call(url: str, key: str, texts: list[str]) -> tuple[list[list[float]], float]:
    request = urllib.request.Request(
        url.rstrip("/") + "/embed",
        data=json.dumps({"texts": texts}).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=180) as response:
        body = json.load(response)
    return body["vectors"], (time.perf_counter() - started) * 1000


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return dot / ((sum(x * x for x in a) ** 0.5) * (sum(y * y for y in b) ** 0.5))


def pct(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(q * (len(ordered) - 1)))]


sources = {
    "tu_host": (os.environ["EMBEDDER_URL"], os.environ["EMBEDDER_KEY"]),
    "modal": (os.environ["MODAL_URL"], os.environ["MODAL_KEY"]),
}
for name, (url, key) in sources.items():
    call(url, key, ["khởi động"])  # làm ấm (Modal có thể mất hàng chục giây nếu GPU nguội)

latency = {name: [] for name in sources}
vectors = {name: [] for name in sources}
for question in QUESTIONS:
    for repeat in range(REPEAT):
        for name, (url, key) in sources.items():
            vec, ms = call(url, key, [question])
            latency[name].append(ms)
            if repeat == 0:
                vectors[name].append(vec[0])

sample = [f"đoạn văn thử số {i} " + "nội dung onboarding " * 20 for i in range(32)]
batch = {name: [call(url, key, sample)[1] for _ in range(3)] for name, (url, key) in sources.items()}
cos = [cosine(a, b) for a, b in zip(vectors["tu_host"], vectors["modal"])]

result = {
    "latency_ms_mot_cau": {n: {"p50": round(pct(v, 0.5)), "p95": round(pct(v, 0.95)), "mean": round(statistics.mean(v)), "n": len(v)} for n, v in latency.items()},
    "latency_ms_lo_32_doan": {n: round(statistics.median(v)) for n, v in batch.items()},
    "cosine_giua_hai_nguon": {"mean": round(statistics.mean(cos), 5), "min": round(min(cos), 5)},
}
json.dump(result, sys.stdout, ensure_ascii=False, indent=1)
print()
