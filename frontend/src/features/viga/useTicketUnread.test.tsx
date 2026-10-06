import { act, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { vigaApi } from "@/features/viga/api";

import { notifyTicketsRead, useTicketUnread } from "./useTicketUnread";

vi.mock("@/features/viga/api", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/features/viga/api")>();
  return { ...original, vigaApi: { getUnreadTickets: vi.fn() } };
});

function Badge({ enabled = true }: { enabled?: boolean }) {
  const count = useTicketUnread(enabled);
  return <span data-testid="count">{count}</span>;
}

beforeEach(() => vi.clearAllMocks());

describe("số ticket có tin chưa xem", () => {
  it("lấy số ngay khi mở và tải lại ngay sau khi người dùng mở một ticket", async () => {
    vi.mocked(vigaApi.getUnreadTickets).mockResolvedValueOnce({ count: 2, ticket_ids: [1, 2] }).mockResolvedValue({ count: 1, ticket_ids: [2] });
    render(<Badge />);

    await waitFor(() => expect(screen.getByTestId("count")).toHaveTextContent("2"));
    act(() => notifyTicketsRead());
    await waitFor(() => expect(screen.getByTestId("count")).toHaveTextContent("1")); // mở một ticket thì trừ 1
  });

  it("tắt thì không gọi máy chủ và luôn là 0; lỗi mạng thì giữ số cũ", async () => {
    render(<Badge enabled={false} />);
    expect(screen.getByTestId("count")).toHaveTextContent("0");
    expect(vigaApi.getUnreadTickets).not.toHaveBeenCalled();
  });

  it("lỗi tạm thời không làm mất số đang hiện", async () => {
    vi.mocked(vigaApi.getUnreadTickets).mockResolvedValueOnce({ count: 3, ticket_ids: [1, 2, 3] }).mockRejectedValue(new Error("mạng"));
    render(<Badge />);

    await waitFor(() => expect(screen.getByTestId("count")).toHaveTextContent("3"));
    act(() => notifyTicketsRead());
    await new Promise((resolve) => setTimeout(resolve, 30));
    expect(screen.getByTestId("count")).toHaveTextContent("3");
  });
});
