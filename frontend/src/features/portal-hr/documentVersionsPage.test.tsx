import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";

import viMessages from "../../../messages/vi.json";
import { portalHrApi } from "@/features/portal-hr/api";
import type {
  DocumentListItemResponseDTO,
  DocumentVersionDetailResponseDTO,
  DocumentVersionResponseDTO,
} from "@/features/portal-hr/dto/responseDTO/portal.response";

import { DocumentVersionsPage } from "./DocumentVersionsPage";

const push = vi.fn();

vi.mock("@/i18n/navigation", () => ({ useRouter: () => ({ push, replace: vi.fn() }) }));
vi.mock("@/features/portal-hr/api", () => {
  class PortalError extends Error {
    readonly code = "unavailable";
    readonly apiCode: string | null = null;
  }
  return {
    PortalError,
    portalHrApi: {
      listDocuments: vi.fn(),
      listDocumentVersions: vi.fn(),
      getDocumentVersion: vi.fn(),
      getCapabilities: vi.fn(),
      listActiveJobs: vi.fn(),
      originalDocumentUrl: (id: number) => `/original/${id}`,
      previewDocumentUrl: (id: number) => `/preview/${id}`,
    },
  };
});
vi.mock("./PdfViewer", () => ({ PdfViewer: ({ url }: { url: string }) => <div data-testid="pdf-viewer" data-url={url} /> }));

const api = vi.mocked(portalHrApi);

const VERSION: DocumentVersionResponseDTO = {
  id: 5,
  version_label: "1.0",
  revision_no: 1,
  state: "CURRENT",
  status: "ACTIVE",
  effective_from: "2026-01-01",
  effective_to: null,
  source: "UPLOAD",
  parent_version_id: null,
  original_filename: "a.docx",
  uploaded_by_name: "Hồng",
  created_at: "2026-09-01T00:00:00Z",
  updated_at: "2026-09-01T00:00:00Z",
  activated_at: null,
  failure_reason: null,
  section_count: 2,
  task_count: 0,
  structure_quality: "GOOD",
  structure_warnings: [],
  ai_split: null,
};

const DOC = {
  id: 9,
  title: "Quy chế nghỉ phép",
  category_name: "Onboarding",
  status: "ACTIVE",
  updated_at: "2026-09-01T00:00:00Z",
  latest_version_id: 5,
  section_count: 2,
  source_key: "nghi-phep",
  category_slug: "onboarding",
  owner_name: "Hồng",
  task_titles: [],
  current_version_label: "1.0",
  version_count: 1,
  draft_count: 0,
  processing_count: 0,
  processing_version_ids: [],
} as DocumentListItemResponseDTO;

function renderPage(documentId = 9) {
  render(
    <NextIntlClientProvider locale="vi" messages={viMessages}>
      <DocumentVersionsPage documentId={documentId} />
    </NextIntlClientProvider>,
  );
}

describe("DocumentVersionsPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    api.listDocuments.mockResolvedValue([DOC]);
    api.listDocumentVersions.mockResolvedValue([VERSION]);
    api.listActiveJobs.mockResolvedValue([]);
    api.getCapabilities.mockResolvedValue({ word_editor: false });
    api.getDocumentVersion.mockResolvedValue({
      version: VERSION,
      document_id: 9,
      document_title: DOC.title,
      markdown: "# Quy chế\n\nNghỉ phép mười hai ngày.",
      can_edit: false,
    } satisfies DocumentVersionDetailResponseDTO);
  });

  it("hiện trang riêng của tài liệu và nút quay lại danh sách", async () => {
    renderPage();

    expect(await screen.findByRole("heading", { name: "Quy chế nghỉ phép" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Quay lại danh sách tài liệu/ }));
    expect(push).toHaveBeenCalledWith("/admin/documents");
  });

  it("báo không tìm thấy khi mã tài liệu không có trong danh sách", async () => {
    renderPage(404);
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /Quay lại danh sách tài liệu/ })).toBeInTheDocument();
  });

  it("báo đang OCR rồi nhắc soát lại chữ khi bản nháp đến từ bản scan", async () => {
    api.listDocumentVersions.mockResolvedValue([{ ...VERSION, ocr: true, state: "PROCESSING", status: "PROCESSING" }]);
    api.getDocumentVersion.mockResolvedValue({
      version: { ...VERSION, ocr: true, state: "PROCESSING", status: "PROCESSING" },
      document_id: 9,
      document_title: DOC.title,
      markdown: "",
      can_edit: false,
    } satisfies DocumentVersionDetailResponseDTO);
    renderPage();
    expect(await screen.findByText(/Đang nhận dạng chữ \(OCR\)/)).toBeInTheDocument();
  });

  it("không hiện ghi chú soát lại OCR trên trang riêng khi bản nháp OCR đã xong", async () => {
    const done = { ...VERSION, ocr: true, state: "DRAFT" as const, status: "DRAFT" as const };
    api.listDocumentVersions.mockResolvedValue([done]);
    api.getDocumentVersion.mockResolvedValue({
      version: done,
      document_id: 9,
      document_title: DOC.title,
      markdown: "# Quy chế\n\nNghỉ phép mười hai ngày.",
      can_edit: true,
    } satisfies DocumentVersionDetailResponseDTO);
    renderPage();
    expect(await screen.findByRole("heading", { name: "Quy chế nghỉ phép" })).toBeInTheDocument();
    await screen.findByText(/Nghỉ phép mười hai ngày/);
    expect(screen.queryByText(/hãy soát lại/i)).toBeNull();
  });

  it("mở sẵn tab Bản gốc bằng trình xem PDF riêng (không nhúng khung của trình duyệt) khi file gốc là PDF", async () => {
    const pdf = { ...VERSION, original_filename: "luat.pdf" };
    api.listDocumentVersions.mockResolvedValue([pdf]);
    api.getDocumentVersion.mockResolvedValue({
      version: pdf,
      document_id: 9,
      document_title: DOC.title,
      markdown: "# Luật\n\nNội dung.",
      can_edit: false,
    } satisfies DocumentVersionDetailResponseDTO);
    const { container } = render(
      <NextIntlClientProvider locale="vi" messages={viMessages}>
        <DocumentVersionsPage documentId={9} />
      </NextIntlClientProvider>,
    );
    await waitFor(() => expect(screen.getByTestId("pdf-viewer")).toBeInTheDocument());
    expect(screen.getByTestId("pdf-viewer")).toHaveAttribute("data-url", "/preview/5");
    expect(container.querySelector("iframe")).toBeNull();
    expect(screen.getByRole("tab", { name: "Bản gốc" })).toHaveAttribute("aria-selected", "true");
    fireEvent.click(screen.getByRole("tab", { name: "Nội dung" }));
    await waitFor(() => expect(screen.queryByTestId("pdf-viewer")).toBeNull());
  });
});
