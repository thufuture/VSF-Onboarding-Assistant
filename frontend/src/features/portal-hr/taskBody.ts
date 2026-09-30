// Nội dung task lưu ở `body_markdown`; tab "Hướng dẫn" của v15 (Vì sao / Điều kiện hoàn thành / Các bước)
// được ghép thành Markdown có 3 đề mục cố định để đọc lại được, không thêm cột mới trong CSDL.
const WHY = "Vì sao phải làm";
const DONE = "Điều kiện hoàn thành";
const STEPS = "Các bước";

export type TaskBodyParts = { why: string; done: string; steps: string[] };

export function parseTaskBody(markdown: string): TaskBodyParts {
  const sections: Record<string, string> = {};
  let current: string | null = null;
  let found = false;
  for (const line of markdown.split("\n")) {
    const heading = /^##\s+(.+?)\s*$/.exec(line);
    if (heading && [WHY, DONE, STEPS].includes(heading[1])) {
      current = heading[1];
      sections[current] = "";
      found = true;
    } else if (current) {
      sections[current] += `${line}\n`;
    }
  }
  if (!found) return { why: "", done: "", steps: markdown.split("\n").filter((l) => l.trim()) };
  const steps = (sections[STEPS] ?? "")
    .split("\n")
    .map((l) => l.replace(/^\s*\d+[.)]\s*/, "").trim())
    .filter(Boolean);
  return { why: (sections[WHY] ?? "").trim(), done: (sections[DONE] ?? "").trim(), steps };
}

export function serializeTaskBody(parts: TaskBodyParts, fallbackTitle: string): string {
  const out: string[] = [];
  if (parts.why.trim()) out.push(`## ${WHY}\n${parts.why.trim()}`);
  if (parts.done.trim()) out.push(`## ${DONE}\n${parts.done.trim()}`);
  const steps = parts.steps.map((s) => s.trim()).filter(Boolean);
  if (steps.length) out.push(`## ${STEPS}\n${steps.map((s, i) => `${i + 1}. ${s}`).join("\n")}`);
  return out.length ? out.join("\n\n") : fallbackTitle;
}
