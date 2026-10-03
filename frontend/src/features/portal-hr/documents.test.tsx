import { act, fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import viMessages from "../../../messages/vi.json";
import { JobProgress } from "@/components/job-progress/JobProgress";
import { portalHrApi } from "@/features/portal-hr/api";
import type {
  DocumentListItemResponseDTO,
  DocumentVersionDetailResponseDTO,
  DocumentVersionResponseDTO,
  JobResponseDTO,
} from "@/features/portal-hr/dto/responseDTO/portal.response";

import { DocumentVersionsModal } from "./DocumentVersionsModal";
import { useJob } from "./useJob";

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
      listDocumentVersions: vi.fn(),
      getDocumentVersion: vi.fn(),
      copyDocumentVersion: vi.fn(),
      updateDocumentVersion: vi.fn(),
      deleteDocumentVersion: vi.fn(),
      activateDocumentVersion: vi.fn(),
      listActiveJobs: vi.fn(),
      getJob: vi.fn(),
      originalDocumentUrl: (id: number) => `/original/${id}`,
    },
  };
});

const api = vi.mocked(portalHrApi);

function wrap(children: ReactNode) {
  return (
    <NextIntlClientProvider locale="vi" messages={viMessages}>
      {children}
    </NextIntlClientProvider>
  );
}

function job(overrides: Partial<JobResponseDTO>): JobResponseDTO {
  return {
    id: 7,
    kind: "ACTIVATE_VERSION",
    status: "RUNNING",
    progress_percent: 0,
    stage: null,
    result: null,
    error: null,
    document_version_id: 2,
    created_at: "2026-10-01T00:00:00Z",
    finished_at: null,
    ...overrides,
  };
}

const MARKDOWN = "# Hồ sơ\n\nNộp giấy tờ.\n\n## Thiết bị\n\nNhận laptop.";

function version(id: number, label: string, state: DocumentVersionResponseDTO["state"], extra: Partial<DocumentVersionResponseDTO> = {}): DocumentVersionResponseDTO {
  return {
    id,
    version_label: label,
    revision_no: id,
    state,
    status: state === "DRAFT" ? "DRAFT" : state === "SUPERSEDED" ? "ARCHIVED" : "ACTIVE",
    effective_from: state === "DRAFT" ? null : "2026-01-01",
    effective_to: null,
    source: "UPLOAD",
    parent_version_id: null,
    original_filename: "tai-lieu.docx",
    uploaded_by_name: "Hồng",
    created_at: "2026-09-01T00:00:00Z",
    updated_at: `2026-09-0${id}T00:00:00Z`,
    activated_at: null,
    failure_reason: null,
    section_count: 2,
    task_count: 0,
    structure_quality: "GOOD",
    structure_warnings: [],
    ai_split: null,
    ...extra,
  };
}

function detailOf(v: DocumentVersionResponseDTO, markdown = MARKDOWN): DocumentVersionDetailResponseDTO {
  return { version: v, document_id: 1, document_title: "Nghỉ phép", markdown, can_edit: v.state === "DRAFT" };
}

const DOC: DocumentListItemResponseDTO = {
  id: 1,
  title: "Nghỉ phép",
  category_name: "Nghỉ phép và nghỉ lễ",
  status: "ACTIVE",
  updated_at: "2026-09-01T00:00:00Z",
  latest_version_id: 1,
  section_count: 2,
  source_key: "nghi-phep",
  category_slug: "nghi-phep",
  owner_name: "Hồng",
  task_titles: [],
  current_version_label: "v1",
  version_count: 2,
  draft_count: 1,
  processing_count: 0,
  processing_version_ids: [],
};

describe("JobProgress", () => {
  it("shows the real percentage, the stage and an accessible progressbar", () => {
    render(<JobProgress percent={45.4} stage="Embedding 12/34" state="running" />);

    const bar = screen.getByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuenow", "45");
    expect(screen.getByText("45%")).toBeInTheDocument();
    expect(screen.getByText("Embedding 12/34")).toBeInTheDocument();
  });

  it("clamps out-of-range values", () => {
    render(<JobProgress percent={140} state="done" />);
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "100");
  });
});

describe("useJob", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.resetAllMocks();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("polls every second until the job finishes, then calls onDone exactly once", async () => {
    const done = vi.fn();
    api.getJob
      .mockResolvedValueOnce(job({ progress_percent: 10, stage: "Đọc" }))
      .mockResolvedValueOnce(job({ progress_percent: 60, stage: "Embedding 5/8" }))
      .mockResolvedValue(job({ status: "SUCCEEDED", progress_percent: 100 }));

    const { result } = renderHook(() => useJob(7, done));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(result.current.job?.progress_percent).toBe(10);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });
    expect(result.current.job?.progress_percent).toBe(60);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });
    expect(result.current.job?.status).toBe("SUCCEEDED");
    expect(done).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    expect(api.getJob).toHaveBeenCalledTimes(3); // đã dừng hỏi sau khi xong
  });

  it("gives up after repeated errors and reports the job as lost", async () => {
    api.getJob.mockRejectedValue(new Error("mạng"));

    const { result } = renderHook(() => useJob(7));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(6000);
    });

    expect(result.current.lost).toBe(true);
  });

  it("does nothing without a job id", async () => {
    renderHook(() => useJob(null));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    expect(api.getJob).not.toHaveBeenCalled();
  });
});

describe("DocumentVersionsModal", () => {
  const v1 = version(1, "v1", "CURRENT");
  const v2 = version(2, "v2 nháp", "DRAFT", { structure_quality: "POOR", structure_warnings: ["NO_STRUCTURE"] });
  const v0 = version(3, "v0", "SUPERSEDED", { task_count: 2 });

  beforeEach(() => {
    vi.resetAllMocks();
    api.listDocumentVersions.mockResolvedValue([v2, v1, v0]);
    api.listActiveJobs.mockResolvedValue([]);
    api.getDocumentVersion.mockImplementation((_doc, id) =>
      Promise.resolve(detailOf([v1, v2, v0].find((v) => v.id === id) as DocumentVersionResponseDTO)),
    );
  });

  function open() {
    const onChanged = vi.fn();
    render(
      wrap(<DocumentVersionsModal doc={DOC} onChanged={onChanged} onClose={vi.fn()} onUploadNewVersion={vi.fn()} />),
    );
    return { onChanged };
  }

  it("lists versions with their state and opens the current one first", async () => {
    open();

    expect(await screen.findByText("v1")).toBeInTheDocument();
    // Chờ phần chi tiết tải xong rồi mới đếm nhãn: lúc đó bản đang áp dụng có nhãn ở danh sách và ở đầu phần chi tiết.
    expect(await screen.findByRole("heading", { name: /v1/ })).toBeInTheDocument();
    expect(screen.getAllByText("Đang áp dụng")).toHaveLength(2);
    expect(screen.getByText("Bản nháp")).toBeInTheDocument();
    expect(screen.getByText("Đã thay thế")).toBeInTheDocument();
    // Bản đang áp dụng không sửa tại chỗ và không có nút kích hoạt.
    expect(screen.queryByRole("button", { name: "Sửa nháp" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Kích hoạt" })).not.toBeInTheDocument();
  });

  it("không gọi lại API liên tục khi vẽ lại (hàm dịch của next-intl đổi tham chiếu mỗi lần render)", async () => {
    open();
    await screen.findByRole("heading", { name: /v1/ });
    await new Promise((resolve) => setTimeout(resolve, 60));

    expect(api.listDocumentVersions).toHaveBeenCalledTimes(1);
    expect(api.getDocumentVersion.mock.calls.length).toBeLessThanOrEqual(2);
  });

  it("warns about a poorly structured draft and offers edit and activate", async () => {
    open();

    fireEvent.click(await screen.findByRole("button", { name: /v2 nháp/ }));

    expect(await screen.findByText(/gần như không có tiêu đề/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sửa nháp" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Kích hoạt" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Xóa nháp" })).toBeInTheDocument();
  });

  it("saves a draft edit with the optimistic-lock timestamp it read", async () => {
    api.updateDocumentVersion.mockResolvedValue({ ...v2, version_label: "v2 sửa" });
    const { onChanged } = open();

    fireEvent.click(await screen.findByRole("button", { name: /v2 nháp/ }));
    fireEvent.click(await screen.findByRole("button", { name: "Sửa nháp" }));
    fireEvent.change(screen.getByLabelText("Nhãn phiên bản"), { target: { value: "v2 sửa" } });
    fireEvent.click(screen.getByRole("button", { name: "Lưu" }));

    await waitFor(() => expect(api.updateDocumentVersion).toHaveBeenCalled());
    expect(api.updateDocumentVersion).toHaveBeenCalledWith(1, 2, {
      expected_updated_at: v2.updated_at,
      markdown: null,
      label: "v2 sửa",
      effective_from: null,
      clear_effective_from: false,
    });
    await waitFor(() => expect(onChanged).toHaveBeenCalled());
  });

  it("shows a clear message when someone else saved the draft first", async () => {
    const { PortalError } = await import("@/features/portal-hr/api");
    api.updateDocumentVersion.mockRejectedValue(new PortalError("unavailable", "VERSION_CONFLICT"));
    open();

    fireEvent.click(await screen.findByRole("button", { name: /v2 nháp/ }));
    fireEvent.click(await screen.findByRole("button", { name: "Sửa nháp" }));
    fireEvent.change(screen.getByLabelText("Nhãn phiên bản"), { target: { value: "khác" } });
    fireEvent.click(screen.getByRole("button", { name: "Lưu" }));

    expect(await screen.findByText(/vừa được người khác lưu/)).toBeInTheDocument();
  });

  it("activates a draft after confirmation and shows the background progress", async () => {
    api.activateDocumentVersion.mockResolvedValue(job({ id: 7, document_version_id: 2 }));
    api.getJob.mockResolvedValue(job({ id: 7, progress_percent: 42, stage: "Embedding 3/8" }));
    open();

    fireEvent.click(await screen.findByRole("button", { name: /v2 nháp/ }));
    fireEvent.click(await screen.findByRole("button", { name: "Kích hoạt" }));
    // Hộp xác nhận mở ra với nút "Kích hoạt" thứ hai (nút xác nhận nằm sau nút ở khung phiên bản).
    const buttons = await screen.findAllByRole("button", { name: "Kích hoạt" });
    fireEvent.click(buttons[buttons.length - 1]);

    await waitFor(() => expect(api.activateDocumentVersion).toHaveBeenCalledWith(1, 2, { effective_from: expect.any(String) }));
    expect(await screen.findByText("Embedding 3/8")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "42");
  });

  it("offers to set a superseded version as current again", async () => {
    open();

    fireEvent.click(await screen.findByRole("button", { name: /v0/ }));

    expect(await screen.findByRole("button", { name: "Đặt làm bản áp dụng" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tạo bản mới từ bản này" })).toBeInTheDocument();
  });

  it("copies a version into a new draft and opens it for editing", async () => {
    const copy = version(9, "v1 (sao chép)", "DRAFT", { parent_version_id: 1, source: "EDITED" });
    api.copyDocumentVersion.mockResolvedValue(copy);
    api.listDocumentVersions.mockResolvedValueOnce([v2, v1, v0]).mockResolvedValue([copy, v2, v1, v0]);
    api.getDocumentVersion.mockImplementation((_doc, id) =>
      Promise.resolve(detailOf([v1, v2, v0, copy].find((v) => v.id === id) as DocumentVersionResponseDTO)),
    );
    open();

    fireEvent.click(await screen.findByRole("button", { name: "Tạo bản mới từ bản này" }));

    await waitFor(() => expect(api.copyDocumentVersion).toHaveBeenCalledWith(1, 1, {}));
    expect(await screen.findByLabelText("Nhãn phiên bản")).toHaveValue("v1 (sao chép)");
  });
});
