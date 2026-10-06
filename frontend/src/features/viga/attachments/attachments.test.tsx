import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { beforeEach, describe, expect, it, vi } from "vitest";

import viMessages from "../../../../messages/vi.json";
import { vigaApi } from "@/features/viga/api";

import { AttachmentList } from "./AttachmentList";
import { AttachmentPicker } from "./AttachmentPicker";
import { checkFile, useAttachments } from "./useAttachments";

vi.mock("@/features/viga/api", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/features/viga/api")>();
  return { ...original, vigaApi: { uploadTicketAttachment: vi.fn(), discardTicketAttachment: vi.fn() } };
});

const t = viMessages.attachments;
const MB = 1024 * 1024;

function file(name: string, type: string, size = 100): File {
  return new File([new Uint8Array(size)], name, { type });
}

function Harness({ onIds }: { onIds: (ids: number[]) => void }) {
  const attachments = useAttachments();
  onIds(attachments.ids);
  return (
    <NextIntlClientProvider locale="vi" messages={viMessages}>
      <AttachmentPicker attachments={attachments} />
    </NextIntlClientProvider>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.stubGlobal("URL", { ...URL, createObjectURL: () => "blob:xem-thu", revokeObjectURL: vi.fn() });
});

describe("kiểm tra tệp trước khi tải", () => {
  it("nhận ảnh và video đúng loại, đúng dung lượng", () => {
    expect(checkFile({ name: "loi.PNG", type: "image/png", size: 5 * MB })).toEqual({ kind: "IMAGE" });
    expect(checkFile({ name: "man-hinh.mp4", type: "video/mp4", size: 40 * MB })).toEqual({ kind: "VIDEO" });
  });

  it("từ chối loại lạ, tệp đổi đuôi và vượt dung lượng", () => {
    expect(checkFile({ name: "ghi-chu.txt", type: "text/plain", size: 10 })).toEqual({ errorKey: "type" });
    expect(checkFile({ name: "gia.png", type: "video/mp4", size: 10 })).toEqual({ errorKey: "type" });
    expect(checkFile({ name: "to.jpg", type: "image/jpeg", size: 11 * MB })).toEqual({ errorKey: "tooLargeImage" });
    expect(checkFile({ name: "dai.mp4", type: "video/mp4", size: 51 * MB })).toEqual({ errorKey: "tooLargeVideo" });
  });
});

describe("chọn và tải ảnh, video đính kèm", () => {
  it("tải ngay khi chọn, giữ mã đã lưu, bỏ một tệp thì gỡ cả trên máy chủ", async () => {
    vi.mocked(vigaApi.uploadTicketAttachment).mockResolvedValue({
      id: 7,
      kind: "IMAGE",
      url: "https://res.cloudinary.test/a.png",
      filename: "loi.png",
      content_type: "image/png",
      size_bytes: 100,
    });
    vi.mocked(vigaApi.discardTicketAttachment).mockResolvedValue();
    let ids: number[] = [];
    render(<Harness onIds={(next) => (ids = next)} />);

    fireEvent.change(screen.getByLabelText(t.pick), { target: { files: [file("loi.png", "image/png")] } });

    await waitFor(() => expect(ids).toEqual([7]));
    expect(vigaApi.uploadTicketAttachment).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "Bỏ loi.png" }));
    await waitFor(() => expect(vigaApi.discardTicketAttachment).toHaveBeenCalledWith(7));
    expect(ids).toEqual([]);
  });

  it("tệp sai loại báo lỗi ngay và không gọi máy chủ", () => {
    render(<Harness onIds={() => undefined} />);

    fireEvent.change(screen.getByLabelText(t.pick), { target: { files: [file("ghi-chu.txt", "text/plain")] } });

    expect(screen.getByRole("alert")).toHaveTextContent(t.errors.type);
    expect(vigaApi.uploadTicketAttachment).not.toHaveBeenCalled();
  });

  it("máy chủ từ chối thì tệp báo lỗi và không có mã để gửi", async () => {
    vi.mocked(vigaApi.uploadTicketAttachment).mockRejectedValue(new Error("boom"));
    let ids: number[] = [1];
    render(<Harness onIds={(next) => (ids = next)} />);

    fireEvent.change(screen.getByLabelText(t.pick), { target: { files: [file("a.png", "image/png")] } });

    expect(await screen.findByRole("alert")).toHaveTextContent(t.errors.failed);
    expect(ids).toEqual([]);
  });
});

describe("hiển thị tệp đã đính kèm", () => {
  it("ảnh bấm mở bản đầy đủ, video có nút điều khiển", () => {
    render(
      <NextIntlClientProvider locale="vi" messages={viMessages}>
        <AttachmentList
          attachments={[
            { id: 1, kind: "IMAGE", url: "https://res.cloudinary.test/a.png", filename: "loi.png", content_type: "image/png", size_bytes: 1 },
            { id: 2, kind: "VIDEO", url: "https://res.cloudinary.test/b.mp4", filename: "man-hinh.mp4", content_type: "video/mp4", size_bytes: 1 },
          ]}
        />
      </NextIntlClientProvider>,
    );

    const list = screen.getByRole("list", { name: t.listLabel });
    expect(within(list).getByRole("link")).toHaveAttribute("href", "https://res.cloudinary.test/a.png");
    expect(within(list).getByLabelText("man-hinh.mp4")).toHaveAttribute("controls");
  });
});
