# -*- coding: utf-8 -*-
"""Thử temperature=0 (và 0.3) cho đường nhanh trên docx không tiêu đề và Hướng dẫn ngày 1, chỉ đo, không đổi mã sản phẩm."""
import asyncio
import json
import sys

sys.path.insert(0, r"D:\Intern-VSF\vsf-onboarding-assistant\docs\chatbot-vsf\plan\plan-portal\Ai-task\thu-nghiem")
sys.path.insert(0, r"D:\Intern-VSF\vsf-onboarding-assistant\backend")
import do_tren_ma_nguon as m
from src.infrastructure.ai.deepseek_adapter import DeepSeekChatCompletion
from src.infrastructure.ai.llm_gate import LlmGate
from src.infrastructure.observability.call_metrics import set_prices


def make(temp):
    class Warm(DeepSeekChatCompletion):
        def _body(self, system_prompt, user_prompt, *, reasoning, stream):
            body = super()._body(system_prompt, user_prompt, reasoning=reasoning, stream=stream)
            if temp is not None:
                body["temperature"] = temp
            return body

    return Warm(base_url=m.env("LLM_BASE_URL"), api_key=m.env("LLM_API_KEY"), model=m.env("LLM_MODEL"), max_retries=2, gate=LlmGate(9, 5))


async def main():
    set_prices(llm_input_per_million=0.30, llm_output_per_million=1.20, embedding_per_thousand=0.0)
    out = {}
    for doc, runs in (("docx-ngay1", 8), ("ngay1", 6)):
        sections = m.load(doc)
        for temp in (None, 0, 0.3):
            llm = make(temp)
            rows = []
            for _ in range(runs):
                row, _detail = await m.one_run(doc, "fast", llm, sections)
                rows.append({k: row.get(k) for k in ("seconds", "tasks", "covered", "dependencies", "empty_steps", "quotes_all_verbatim", "order_source")})
            tasks = sorted(r["tasks"] for r in rows)
            print(doc, "temp", temp, "tasks", tasks, "covered", [r["covered"] for r in rows].count(rows[0]["covered"]), "sec", sorted(r["seconds"] for r in rows)[len(rows) // 2], flush=True)
            out[f"{doc}|{temp}"] = rows
    open(r"C:\Users\DELL\AppData\Local\Temp\claude\d--Intern-VSF-vsf-onboarding-assistant\b4633c15-95e8-4056-babb-9fbfae54bca5\scratchpad\temp_experiment.json", "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))


asyncio.run(main())
