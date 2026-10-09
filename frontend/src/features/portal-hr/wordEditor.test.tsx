import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import viMessages from "../../../messages/vi.json";
import { portalHrApi } from "@/features/portal-hr/api";

import { WordEditorPanel } from "./WordEditorPanel";

vi.mock("@/features/portal-hr/api", () => ({
  portalHrApi: {
    openEditorSession: vi.fn(),
    saveEditorSession: vi.fn(),
    exportVersionUrl: (doc: number, ver: number, format: string) => `/export/${doc}/${ver}?format=${format}`,
  },
}));

const api = vi.mocked(portalHrApi);

function renderPanel() {
  const onSaved = vi.fn();
  const onCancel = vi.fn();
  render(
    <NextIntlClientProvider locale="vi" messages={viMessages}>
      <WordEditorPanel documentId={1} onCancel={onCancel} onSaved={onSaved} versionId={2} />
    </NextIntlClientProvider>,
  );
  return { onSaved, onCancel };
}

describe("WordEditorPanel", () => {
  const created: Array<{ id: string; config: Record<string, unknown> }> = [];

  beforeEach(() => {
    vi.resetAllMocks();
    created.length = 0;
    (window as unknown as { DocsAPI: unknown }).DocsAPI = {
      DocEditor: class {
        destroyEditor = vi.fn();
        constructor(id: string, config: Record<string, unknown>) {
          created.push({ id, config });
        }
      },
    };
  });

  afterEach(() => {
    delete (window as unknown as { DocsAPI?: unknown }).DocsAPI;
  });

  it("mở phiên, dựng trình soạn thảo với cấu hình đã ký và không còn nút xuất ở thanh trên (chọn khi Lưu)", async () => {
    api.openEditorSession.mockResolvedValue({
      api_js_url: "http://oo.test/api.js",
      config: { token: "abc", documentType: "word" },
      document_key: "key-1",
    });
    renderPanel();

    await waitFor(() => expect(created).toHaveLength(1));
    expect(created[0].id).toBe("word-editor-host");
    expect(created[0].config.token).toBe("abc");
    expect(screen.queryByRole("link", { name: /Xuất/ })).not.toBeInTheDocument();
  });

  it("Lưu hỏi định dạng file gốc (PDF hoặc Markdown) rồi mới gửi lệnh lưu", async () => {
    api.openEditorSession.mockResolvedValue({ api_js_url: "x", config: {}, document_key: "key-9" });
    api.saveEditorSession.mockResolvedValue({ ok: true, changed: true });
    const { onSaved } = renderPanel();

    await waitFor(() => expect(created).toHaveLength(1));
    fireEvent.click(screen.getByRole("button", { name: /^Lưu$/ }));
    expect(api.saveEditorSession).not.toHaveBeenCalled();
    expect(await screen.findByText("Lưu tài liệu")).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /^Word \(\.docx\)/ })).toBeChecked();
    expect(screen.getByRole("radio", { name: /^PDF/ })).not.toBeChecked();

    fireEvent.click(screen.getByRole("radio", { name: /^Markdown/ }));
    fireEvent.click(screen.getAllByRole("button", { name: /^Lưu$/ }).at(-1) as HTMLElement);
    await waitFor(() => expect(api.saveEditorSession).toHaveBeenCalledWith(1, 2, "key-9", "markdown"));
    await waitFor(() => expect(onSaved).toHaveBeenCalledWith("markdown", true));
  });

  it("Hủy đóng mà không gửi lệnh lưu nào", async () => {
    api.openEditorSession.mockResolvedValue({ api_js_url: "x", config: {}, document_key: "key-9" });
    const { onCancel, onSaved } = renderPanel();

    await waitFor(() => expect(created).toHaveLength(1));
    fireEvent.click(screen.getByRole("button", { name: /Hủy/ }));
    expect(onCancel).toHaveBeenCalled();
    expect(api.saveEditorSession).not.toHaveBeenCalled();
    expect(onSaved).not.toHaveBeenCalled();
  });

  it("báo lỗi rõ khi không mở được phiên", async () => {
    api.openEditorSession.mockRejectedValue(new Error("down"));
    renderPanel();
    expect(await screen.findByRole("alert")).toHaveTextContent(/Không mở được trình soạn thảo/);
  });
});
