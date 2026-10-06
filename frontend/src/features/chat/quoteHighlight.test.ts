import { describe, expect, it } from "vitest";

import { findQuoteRange } from "./quoteHighlight";

function rootWith(html: string): HTMLElement {
  const root = document.createElement("div");
  root.innerHTML = html;
  document.body.appendChild(root);
  return root;
}

describe("findQuoteRange", () => {
  it("tìm đúng đoạn dù khác ký hiệu danh sách, khoảng trắng và in hoa", () => {
    const root = rootWith("<h3>2. Hồ sơ</h3><ul><li>CV.</li><li>Lý lịch tư pháp (bản chính, còn hạn 3 tháng).</li></ul>");

    const range = findQuoteRange(root, "• CV. • LÝ LỊCH  tư pháp (bản chính, còn hạn **3 tháng**).");

    expect(range?.toString()).toBe("CV.Lý lịch tư pháp (bản chính, còn hạn 3 tháng"); // dấu câu ở cuối không thuộc phần khớp
  });

  it("đoạn trích nằm xuyên nhiều thẻ vẫn ôm đúng đầu và cuối", () => {
    const root = rootWith("<p>Nhận laptop tại <b>tầng 12</b> của tòa nhà, mang theo thẻ.</p>");

    const range = findQuoteRange(root, "tại tầng 12 của tòa nhà");

    expect(range?.toString()).toBe("tại tầng 12 của tòa nhà");
  });

  it("chỉ tô đoạn đầu tiên khớp và trả null khi không thấy hoặc quá ngắn", () => {
    const root = rootWith("<p>Gửi email tới support@vinsmartfuture.tech để được hỗ trợ.</p><p>Gửi email tới support@vinsmartfuture.tech</p>");

    const range = findQuoteRange(root, "Gửi email tới support@vinsmartfuture.tech");
    expect(range?.startContainer).toBe(root.firstElementChild?.firstChild);

    expect(findQuoteRange(root, "Hộp thư không có trong tài liệu này")).toBeNull();
    expect(findQuoteRange(root, "a b")).toBeNull();
    expect(findQuoteRange(root, "**")).toBeNull();
  });

  it("câu trích bị rút gọn đuôi vẫn tô được phần đầu", () => {
    const root = rootWith("<p>Chương trình Đào tạo Hội nhập là bắt buộc với mọi nhân sự mới của công ty.</p>");

    const range = findQuoteRange(root, "Chương trình Đào tạo Hội nhập là bắt buộc với mọi nhân sự mới, kể cả thực tập sinh");

    expect(range).not.toBeNull();
    expect(range?.toString().startsWith("Chương trình Đào tạo")).toBe(true);
  });
});
