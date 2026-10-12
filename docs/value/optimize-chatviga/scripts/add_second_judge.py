"""Thêm giám khảo thứ hai (OpenRouter anthropic/claude-haiku-5.5 mặc định, hoặc Groq openai/gpt-oss-120b) vào các kết quả đã chấm bằng DeepSeek, để tính độ đồng thuận hai giám khảo.

Groq gói miễn phí giới hạn 8.000 token/phút và 200.000 token/ngày cho mỗi mô hình (OpenRouter trả phí theo token, rất rẻ), nên script:
  - chạy tuần tự, giãn lệnh để không vượt ~7.000 token/phút;
  - dừng khi tổng token đã dùng vượt --token-budget (mặc định 180.000), phần chưa chấm để lần sau (--resume bỏ qua câu đã có điểm Groq);
  - đọc khóa từ tệp ngoài repo (biến môi trường JUDGE_KEY_FILE), không lưu khóa ở đâu trong repo.
Chỉ ghi thêm khóa `giám_khảo_<tên>` (haiku hoặc groq) vào `ket-qua/<nhãn>/điểm_lượt_1.jsonl`, không đổi gì khác.

Chạy từ gốc repo:
  JUDGE_KEY_FILE=<tệp> PYTHONIOENCODING=utf-8 PYTHONPATH=backend backend/.venv/Scripts/python.exe docs/value/optimize-chatviga/scripts/add_second_judge.py --label F_A_on [--limit 38]
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import score_benchmark as sb  # noqa: E402

PROVIDERS = {
    # tên khóa kết quả, url, mô hình, tham số thêm, token/phút tối đa
    "openrouter": ("haiku", "https://openrouter.ai/api/v1/chat/completions", "anthropic/claude-haiku-5.5", {"temperature": 0, "max_tokens": 1500, "reasoning": {"enabled": False}}, 200_000),
    "groq": ("groq", "https://api.groq.com/openai/v1/chat/completions", "openai/gpt-oss-120b", {"temperature": 0, "max_tokens": 1500, "reasoning_effort": "low"}, 7000),
}


class PacedJudge(sb.Judge):
    """Giám khảo có giãn lệnh theo ngân sách token mỗi phút và tổng ngân sách ngày."""

    def __init__(self, provider: str, key: str, token_budget: int) -> None:
        name, url, model, extra, self.tpm = PROVIDERS[provider]
        super().__init__(name, url, key, model, extra)
        self.next_free = 0.0
        self.budget = token_budget
        self.lock = asyncio.Lock()

    @property
    def used(self) -> int:
        return self.tokens_in + self.tokens_out

    async def ask(self, client: httpx.AsyncClient, prompt: str) -> dict | None:
        async with self.lock:  # khóa chỉ để xếp lịch giãn lệnh; phần gọi mạng chạy song song
            if self.used >= self.budget:
                return None
            estimate = len(prompt) / 3.0 + 600  # ước lượng token vào + ra
            wait = self.next_free - time.monotonic()
            self.next_free = max(self.next_free, time.monotonic()) + estimate / self.tpm * 60
        if wait > 0:
            await asyncio.sleep(wait)
        body: dict[str, Any] = {"model": self.model, "messages": [{"role": "user", "content": prompt}], **self.extra}
        for attempt in range(4):
            try:
                response = await client.post(self.url, json=body, headers={"Authorization": f"Bearer {self.key}"}, timeout=180)
                if response.status_code == 429:
                    await asyncio.sleep(float(response.headers.get("retry-after", 20)) + attempt * 5)
                    continue
                response.raise_for_status()
                data = response.json()
                usage = data.get("usage", {})
                self.tokens_in += usage.get("prompt_tokens", 0)
                self.tokens_out += usage.get("completion_tokens", 0)
                self.calls += 1
                content = data["choices"][0]["message"].get("content") or ""
                return json.loads(content[content.find("{") : content.rfind("}") + 1])
            except (httpx.HTTPError, json.JSONDecodeError, KeyError) as error:
                if os.environ.get("JUDGE_DEBUG"):
                    detail = getattr(getattr(error, "response", None), "text", "")[:200].replace(self.key, "***")
                    print(f"  lỗi lần {attempt + 1}: {type(error).__name__} {detail}", flush=True)
                await asyncio.sleep(2 + attempt * 3)
        return None


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--provider", default="openrouter", choices=sorted(PROVIDERS))
    parser.add_argument("--limit", type=int, default=None, help="số câu chấm tối đa trong lần này")
    parser.add_argument("--token-budget", type=int, default=5_000_000)
    parser.add_argument("--golden", default=str(sb.BASE / "golden_v0_nhap.jsonl"))
    args = parser.parse_args()
    key = Path(os.environ["JUDGE_KEY_FILE"]).read_text(encoding="utf-8").strip()
    judge = PacedJudge(args.provider, key, args.token_budget)
    gold = sb.load_gold(Path(args.golden))
    sections = {s["section_id"]: s for s in json.loads((sb.BASE / "kho_muc_bench.json").read_text(encoding="utf-8"))}
    out_dir = sb.DIR / "ket-qua" / args.label
    records = {json.loads(line)["id"]: json.loads(line) for line in (out_dir / "lượt_1.jsonl").read_text(encoding="utf-8").splitlines()}
    target = out_dir / "điểm_lượt_1.jsonl"
    rows = [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()]
    todo = [r for r in rows if r.get("chế_độ_chấm") and r.get(f"giám_khảo_{judge.name}") is None]
    if args.limit:
        todo = todo[: args.limit]
    print(f"[{args.label}] cần chấm {len(todo)} câu bằng {judge.name}", flush=True)
    semaphore = asyncio.Semaphore(int(os.environ.get("JUDGE_PARALLEL", "2")))
    done = 0

    async def work(client: httpx.AsyncClient, row: dict) -> None:
        nonlocal done
        async with semaphore:
            if judge.used >= judge.budget:
                return
            out = await sb.judge_one(client, [judge], records[row["id"]], gold[row["id"]], "golden", sections)
            if out.get(f"giám_khảo_{judge.name}") is not None:
                row[f"giám_khảo_{judge.name}"] = out[f"giám_khảo_{judge.name}"]
            done += 1
            if done % 10 == 0:
                print(f"  {done}/{len(todo)}  token đã dùng {judge.used}", flush=True)

    async with httpx.AsyncClient() as client:
        await asyncio.gather(*(work(client, row) for row in todo))
    target.write_text("\n".join(json.dumps(r, ensure_ascii=False, default=str) for r in rows) + "\n", encoding="utf-8")
    print(f"xong: {judge.calls} lệnh, {judge.tokens_in} token vào, {judge.tokens_out} token ra")


if __name__ == "__main__":
    asyncio.run(main())
