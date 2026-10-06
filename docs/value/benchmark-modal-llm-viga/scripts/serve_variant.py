# -*- coding: utf-8 -*-
"""Máy chủ Viga thử cho benchmark: giống hệt backend thật, chỉ khác công tắc "suy luận ẩn" (thinking) theo từng bước LLM.

Không sửa mã nguồn sản phẩm: bọc `DeepSeekChatCompletion.complete_json` để ép `reasoning=False` cho các bước được chọn
(nhận biết bước bằng `call_context.operation`: viga.route, chat.rewrite, chat.answer). Langfuse bị tắt để không đẩy nội dung
câu hỏi của bộ thử lên dịch vụ ngoài; bảng `llm_calls` vẫn ghi đủ token, độ trễ, chi phí.

Chạy (từ thư mục backend, dùng venv):  python <đường dẫn>/serve_variant.py --off viga.route,chat.rewrite --port 8001
`--off` rỗng = giữ nguyên hành vi hiện tại (mọi bước đều bật suy luận).
"""

import argparse
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[4] / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)  # config đọc ../.env và .env theo thư mục chạy
os.environ["LANGFUSE_ENABLED"] = "false"
os.environ["JOB_WORKER_ENABLED"] = "false"  # không tranh việc nền với backend Docker dùng chung DB

parser = argparse.ArgumentParser()
parser.add_argument("--off", default="", help="các operation tắt suy luận, cách nhau bởi dấu phẩy")
parser.add_argument("--port", type=int, default=8001)
args = parser.parse_args()
OFF = {name.strip() for name in args.off.split(",") if name.strip()}

from src.infrastructure.ai import deepseek_adapter  # noqa: E402
from src.infrastructure.observability import call_metrics  # noqa: E402

_original = deepseek_adapter.DeepSeekChatCompletion.complete_json


async def _patched(self, **kwargs):  # type: ignore[no-untyped-def]
    if call_metrics._current().operation in OFF:
        kwargs["reasoning"] = False
    return await _original(self, **kwargs)


deepseek_adapter.DeepSeekChatCompletion.complete_json = _patched  # type: ignore[method-assign]

import uvicorn  # noqa: E402

print(f"[benchmark] suy luận TẮT ở: {sorted(OFF) or 'không bước nào (hiện trạng)'} · cổng {args.port}", flush=True)
uvicorn.run("src.main:app", host="127.0.0.1", port=args.port, log_level="warning")
