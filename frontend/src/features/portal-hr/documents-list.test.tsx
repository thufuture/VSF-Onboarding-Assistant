import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";

import viMessages from "../../../messages/vi.json";
import { portalHrApi } from "@/features/portal-hr/api";
import type { DocumentListItemResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

import { DocumentsListPage } from "./DocumentsListPage";

vi.mock("@/features/portal-hr/api", () => {
  class PortalError extends Error {
    readonly code: string;
    readonly apiCode: string | null;
    constructor(code: string, apiCode: string | null = null) {
      super(apiCode ?? code);
      this.code = code;
      this.apiCode = apiCode;
    }
  }
  return {
    PortalError,
    portalHrApi: {
      listDocuments: vi.fn(),
      listDocumentCategories: vi.fn(),
      listActiveJobs: vi.fn(),
      getJob: vi.fn(),
      uploadDocument: vi.fn(),
      updateDocument: vi.fn(),
    },
  };
});
vi.mock("@/i18n/navigation", () => ({
  Link: ({ href, children }: { href: string; children: React.ReactNode }) => <a href={href}>{children}</a>,
  usePathname: () => "/admin/documents",
  useRouter: () => ({ replace: vi.fn() }),
}));

const api = vi.mocked(portalHrApi);
const t = viMessages.portalDocuments;

function doc(id: number, title: string, category: string, slug: string, updatedAt: string): DocumentListItemResponseDTO {
  return {
    id,
    title,
    category_name: category,
    status: "ACTIVE",
    updated_at: updatedAt,
    latest_version_id: id * 10,
    section_count: 12,
    source_key: `portal-${id}`,
    category_slug: slug,
    owner_name: "Phạm Thị Hồng",
    task_titles: [],
    current_version_label: "1.0",
    version_count: 1,
    draft_count: 0,
    processing_count: 0,
    processing_version_ids: [],
  };
}

function renderPage() {
  render(
    <NextIntlClientProvider locale="vi" messages={viMessages}>
      <DocumentsListPage />
    </NextIntlClientProvider>,
  );
}

beforeEach(() => {
  vi.resetAllMocks();
  api.listDocuments.mockResolvedValue([
    doc(1, "Hướng dẫn ngày 1 onboarding", "Onboarding", "onboarding", "2026-10-01T08:00:00"),
    doc(2, "Các trường hợp ngoại lệ ngày 1", "Tài liệu khác", "tai-lieu-khac", "2026-09-20T08:00:00"),
  ]);
  api.listDocumentCategories.mockResolvedValue([
    { slug: "onboarding", name: "Onboarding" },
    { slug: "tai-lieu-khac", name: "Tài liệu khác" },
  ]);
  api.listActiveJobs.mockResolvedValue([]);
});

describe("Trang Tài liệu của HR", () => {
  it("chữ dài bị cắt trong ô nhưng đọc đủ khi trỏ chuột (thuộc tính title), bảng không trượt ngang", async () => {
    renderPage();

    const title = await screen.findByText("Hướng dẫn ngày 1 onboarding");
    expect(title).toHaveAttribute("title", "Hướng dẫn ngày 1 onboarding");
    expect(screen.getByText("portal-1")).toHaveAttribute("title", "portal-1");
    expect(screen.getByRole("table").querySelectorAll("col")).toHaveLength(8); // bố cục cột cố định theo phần trăm
  });

  it("lọc theo ngày cập nhật: từ ngày, đến ngày và xóa ngày", async () => {
    renderPage();
    await screen.findByText("Hướng dẫn ngày 1 onboarding");

    fireEvent.change(screen.getByLabelText(t.filter.from), { target: { value: "2026-09-25" } });
    expect(screen.getByText("Hướng dẫn ngày 1 onboarding")).toBeInTheDocument();
    expect(screen.queryByText("Các trường hợp ngoại lệ ngày 1")).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(t.filter.from), { target: { value: "" } });
    fireEvent.change(screen.getByLabelText(t.filter.to), { target: { value: "2026-09-25" } });
    expect(screen.getByText("Các trường hợp ngoại lệ ngày 1")).toBeInTheDocument();
    expect(screen.queryByText("Hướng dẫn ngày 1 onboarding")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: t.filter.clearDates }));
    expect(screen.getByText("Hướng dẫn ngày 1 onboarding")).toBeInTheDocument();
    expect(screen.getByText("Các trường hợp ngoại lệ ngày 1")).toBeInTheDocument();
  });

  it("chọn danh mục bằng danh sách thiết kế riêng chỉ có Onboarding và Tài liệu khác, tải lên gửi đúng mã nhóm", async () => {
    api.uploadDocument.mockResolvedValue({
      document_id: 3,
      version_id: 30,
      job_id: null,
      reused: false,
      structure_quality: "GOOD",
    } as never);
    renderPage();
    await screen.findByText("Hướng dẫn ngày 1 onboarding");

    fireEvent.click(screen.getByRole("button", { name: new RegExp(t.addDocument ?? "Thêm tài liệu") }));
    fireEvent.click(await waitFor(() => document.getElementById("up-cat")!));

    const list = within(await screen.findByRole("listbox"));
    expect(list.getAllByRole("option")).toHaveLength(2); // chỉ hai nhóm
    expect(list.getByText("Ngày đầu, giấy tờ, thiết bị, quy định cần biết")).toBeInTheDocument();
    fireEvent.click(list.getByText("Tài liệu khác"));
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();

    const file = new File(["nội dung"], "quy-dinh.docx", { type: "application/octet-stream" });
    fireEvent.change(document.querySelector('input[type="file"]')!, { target: { files: [file] } });
    fireEvent.change(screen.getByLabelText(t.upload.name), { target: { value: "Quy định mới" } });
    fireEvent.submit(document.getElementById("doc-upload")!); // jsdom không coi tệp gán bằng mã là đã chọn nên bỏ qua kiểm tra `required` của nút

    await waitFor(() => expect(api.uploadDocument).toHaveBeenCalled());
    const form = api.uploadDocument.mock.calls[0]![0] as FormData;
    expect(form.get("category_slug")).toBe("tai-lieu-khac");
  });
});
