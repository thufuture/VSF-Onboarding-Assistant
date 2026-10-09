import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";

import viMessages from "../../../messages/vi.json";
import { portalHrApi } from "@/features/portal-hr/api";
import type { VersionComparisonResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

import { VersionComparePanel } from "./VersionComparePanel";

vi.mock("@/features/portal-hr/api", () => ({
  portalHrApi: { compareDocumentVersion: vi.fn() },
}));

const api = vi.mocked(portalHrApi);

function renderPanel() {
  return render(
    <NextIntlClientProvider locale="vi" messages={viMessages}>
      <VersionComparePanel documentId={1} versionId={2} />
    </NextIntlClientProvider>,
  );
}

const COMPARISON: VersionComparisonResponseDTO = {
  has_base: true,
  base_version_id: 1,
  base_version_label: "v1",
  base_reason: "parent",
  added: 1,
  removed: 0,
  modified: 1,
  unchanged: 1,
  sections: [
    {
      status: "modified",
      heading: "Điều 2",
      old_heading: null,
      segments: [
        { op: "equal", text: "Nghỉ phép năm là " },
        { op: "delete", text: "mười hai" },
        { op: "insert", text: "mười lăm" },
        { op: "equal", text: " ngày." },
      ],
      added_words: 2,
      removed_words: 2,
    },
    { status: "added", heading: "Điều 4", old_heading: null, segments: [{ op: "insert", text: "Làm từ xa." }], added_words: 2, removed_words: 0 },
    { status: "unchanged", heading: "Điều 1", old_heading: null, segments: [], added_words: 0, removed_words: 0 },
  ],
  recompute: { chunks_total: 10, chunks_reused: 8, chunks_to_embed: 2, estimated_seconds: 1 },
};

describe("VersionComparePanel", () => {
  beforeEach(() => vi.resetAllMocks());

  it("hiện mục đã đổi, từng từ thêm/xóa và ước lượng embedding", async () => {
    api.compareDocumentVersion.mockResolvedValue(COMPARISON);
    const { container } = renderPanel();

    expect(await screen.findByText(/So với bản “v1”/)).toBeInTheDocument();
    expect(screen.getByText("Điều 2")).toBeInTheDocument();
    // Chỉ rõ ký tự khác: "mười hai" -> "mười lăm" chỉ đánh dấu đậm phần "hai" và "lăm".
    expect(container.querySelector("del[data-strong=true]")?.textContent).toBe("hai");
    expect(container.querySelector("ins[data-strong=true]")?.textContent).toBe("lăm");
    expect(screen.getByText(/khoảng 2\/10 đoạn/)).toBeInTheDocument();
    // Mặc định chỉ hiện mục đã đổi; chuyển "Tất cả mục" mới thấy mục giữ nguyên.
    expect(screen.queryByText("Điều 1")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Tất cả mục" }));
    expect(screen.getByText("Điều 1")).toBeInTheDocument();
  });

  it("bản đầu tiên chưa có gì để so sánh", async () => {
    api.compareDocumentVersion.mockResolvedValue({
      ...COMPARISON,
      has_base: false,
      base_version_id: null,
      base_version_label: null,
      base_reason: null,
      sections: [],
      recompute: null,
    });
    renderPanel();
    expect(await screen.findByText(/bản đầu tiên của tài liệu/)).toBeInTheDocument();
  });

  it("lỗi gọi API chỉ báo trong tab, không làm hỏng cả cửa sổ", async () => {
    api.compareDocumentVersion.mockRejectedValue(new Error("boom"));
    renderPanel();
    await waitFor(() => expect(screen.getByText(/Không so sánh được/)).toBeInTheDocument());
  });
});
