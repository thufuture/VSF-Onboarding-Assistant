/** Tên highlight trong CSS Custom Highlight API; kiểu dáng ở `app/globals.css` (`::highlight(source-quote)`). */
export const QUOTE_HIGHLIGHT = "source-quote";

// Chỉ giữ chữ và số: bỏ ký hiệu danh sách `* `, `**`, dấu gạch thoát, khoảng trắng, xuống dòng và dấu câu thừa, nên câu trích
// của Viga/AI khớp được với văn bản đã dựng từ Markdown dù khác định dạng (cùng tinh thần `text_match.py` ở backend).
const KEEP = /[\p{L}\p{N}]/u;
const MIN_NEEDLE = 8;

type Mark = { node: Text; offset: number };

function squash(text: string): string {
  let out = "";
  for (const char of text.normalize("NFC")) {
    if (KEEP.test(char)) out += char.toLowerCase();
  }
  return out;
}

/**
 * Tìm đoạn trích trong các nút chữ dưới `root` và trả về `Range` ôm đúng đoạn đó; không thấy thì `null`.
 * Đoạn trích quá ngắn (dưới 8 chữ/số) không tô vì dễ trùng nhầm.
 */
export function findQuoteRange(root: Node, quote: string): Range | null {
  const needle = squash(quote);
  if (needle.length < MIN_NEEDLE) return null;

  const doc = root.ownerDocument ?? (root as Document);
  const walker = doc.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let hay = "";
  const marks: Mark[] = [];
  for (let node = walker.nextNode() as Text | null; node; node = walker.nextNode() as Text | null) {
    const text = node.data;
    let offset = 0;
    for (const char of text) {
      if (KEEP.test(char)) {
        const lower = char.toLowerCase();
        for (let i = 0; i < lower.length; i += 1) marks.push({ node, offset });
        hay += lower;
      }
      offset += char.length;
    }
  }

  // Khớp cả đoạn; nếu mô hình rút gọn đuôi câu thì thử phần đầu đủ dài để vẫn tô được chỗ bắt đầu.
  const attempts = [needle, needle.slice(0, Math.max(MIN_NEEDLE, Math.floor(needle.length * 0.6)))];
  for (const attempt of attempts) {
    const index = hay.indexOf(attempt);
    if (index === -1) continue;
    const first = marks[index];
    const last = marks[index + attempt.length - 1];
    if (!first || !last) continue;
    const range = doc.createRange();
    range.setStart(first.node, first.offset);
    range.setEnd(last.node, last.offset + 1);
    return range;
  }
  return null;
}

type HighlightRegistry = { set(name: string, value: unknown): void; delete(name: string): void };

/** Tô `range` bằng CSS Custom Highlight API (không sửa DOM do React quản lý). Trình duyệt chưa hỗ trợ thì trả `null`. */
export function applyQuoteHighlight(range: Range): (() => void) | null {
  const registry = (globalThis as { CSS?: { highlights?: HighlightRegistry } }).CSS?.highlights;
  const HighlightCtor = (globalThis as { Highlight?: new (...ranges: Range[]) => unknown }).Highlight;
  if (!registry || !HighlightCtor) return null;
  registry.set(QUOTE_HIGHLIGHT, new HighlightCtor(range));
  return () => registry.delete(QUOTE_HIGHLIGHT);
}
