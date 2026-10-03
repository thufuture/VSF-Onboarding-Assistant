import { fireEvent, render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import viMessages from "../../../messages/vi.json";
import type { AiTaskProposalResponseDTO } from "@/features/portal-hr/dto/responseDTO/portal.response";

import { AiRoadmapReview, type Review } from "./AiRoadmapReview";

vi.mock("@/features/chat/DocumentModal", () => ({
  DocumentModal: ({ documentTitle, sectionHeading, quote }: { documentTitle: string; sectionHeading: string | null; quote?: string | null }) => (
    <div data-quote={quote ?? ""} role="dialog" aria-label="tài liệu">
      {`Mở: ${documentTitle} / ${sectionHeading}`}
    </div>
  ),
}));

const t = viMessages.portalHr.propose;

function proposal(title: string): AiTaskProposalResponseDTO {
  return {
    title,
    summary: `Vì sao: ${title}`,
    instructions_markdown: "- Bước 1\n- Bước 2",
    done_criteria: ["Đã nộp"],
    estimated_minutes: 20,
    source_chunks: [{ document_section_id: 1, chunk_id: 1, quote: `Trích dẫn của ${title}` } as never],
    confidence: "HIGH",
    warnings: [],
    task_group: "PROFILE",
  };
}

function Harness({ onCreate }: { onCreate: () => void }) {
  const [reviews, setReviews] = useState<Review[]>([
    { key: 101, proposal: proposal("Nộp hồ sơ"), status: "pending" },
    { key: 102, proposal: proposal("Nhận laptop"), status: "pending" },
  ]);
  return (
    <NextIntlClientProvider locale="vi" messages={viMessages}>
      <AiRoadmapReview busy={false} dayTitle="Ngày 1" onChange={setReviews} onCreate={onCreate} onReset={vi.fn()} reviews={reviews} />
    </NextIntlClientProvider>
  );
}

const create = () => screen.getByRole("button", { name: new RegExp(t.addToTasks) });

describe("Roadmap AI đề xuất", () => {
  it("hiện các đề xuất như roadmap và chỉ cho thêm vào Quản lý task khi không còn đề xuất chờ xem", () => {
    const onCreate = vi.fn();
    render(<Harness onCreate={onCreate} />);

    expect(screen.getByText("Ngày 1")).toBeInTheDocument();
    expect(screen.getByText("Nộp hồ sơ")).toBeInTheDocument();
    expect(create()).toBeDisabled();

    const accept = screen.getAllByRole("button", { name: t.actions.accept });
    fireEvent.click(accept[0]!);
    expect(create()).toBeDisabled(); // còn một đề xuất chờ xem
    fireEvent.click(screen.getAllByRole("button", { name: t.actions.accept })[1]!);
    expect(create()).toBeEnabled();
    fireEvent.click(create());
    expect(onCreate).toHaveBeenCalledTimes(1);
  });

  it("chấp nhận tất cả đề xuất chờ xem trong một lần bấm", () => {
    render(<Harness onCreate={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: new RegExp(t.acceptPending) }));
    expect(create()).toBeEnabled();
    expect(screen.getByRole("button", { name: new RegExp(t.acceptPending) })).toBeDisabled();
  });

  it("xem đúng đoạn nguồn, sửa đề xuất (thành Đã sửa), nhân bản và bỏ có hộp xác nhận", () => {
    render(<Harness onCreate={vi.fn()} />);

    fireEvent.click(screen.getAllByRole("button", { name: t.actions.source })[0]!);
    expect(within(screen.getByRole("dialog")).getByText("“Trích dẫn của Nộp hồ sơ”")).toBeInTheDocument();
    fireEvent.click(within(screen.getByRole("dialog")).getAllByRole("button", { name: viMessages.portalHr.stage.close })[0]!);

    fireEvent.click(screen.getAllByRole("button", { name: t.actions.edit })[0]!);
    fireEvent.change(screen.getByLabelText(t.edit.name), { target: { value: "Nộp hồ sơ ngày đầu" } });
    fireEvent.click(screen.getByRole("button", { name: t.edit.save }));
    expect(screen.getByText("Nộp hồ sơ ngày đầu")).toBeInTheDocument();
    expect(screen.getByText(t.status.edited)).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: t.actions.duplicate })[1]!);
    expect(screen.getByText(/Nhận laptop \(bản sao\)/)).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: t.actions.remove })[0]!);
    expect(screen.getByText("Nộp hồ sơ ngày đầu")).toBeInTheDocument(); // chưa xóa khi chưa xác nhận
    fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: t.remove.confirm }));
    expect(screen.queryByText("Nộp hồ sơ ngày đầu")).not.toBeInTheDocument();
  });
});

describe("Nguồn của đề xuất", () => {
  it("mở tài liệu gốc tại đúng mục và đúng đoạn trích, kèm tiên quyết", () => {
    const withOrigin: Review[] = [
      {
        key: 201,
        proposal: {
          ...proposal("Cài Outlook"),
          source_chunks: [{ document_section_id: 8, quote: "Đăng nhập Outlook và Teams", heading: "8. Nhận laptop" }],
          prerequisites: ["Nhận laptop"],
        },
        status: "pending",
        origin: { versionId: 31, title: "Hướng dẫn ngày 1", label: "1.0" },
      },
    ];
    render(
      <NextIntlClientProvider locale="vi" messages={viMessages}>
        <AiRoadmapReview busy={false} dayTitle="Ngày 1" onChange={vi.fn()} onCreate={vi.fn()} onReset={vi.fn()} reviews={withOrigin} />
      </NextIntlClientProvider>,
    );

    fireEvent.click(screen.getAllByRole("button", { name: t.actions.source })[0]!);
    const dialog = within(screen.getByRole("dialog"));
    expect(dialog.getByText("Hướng dẫn ngày 1")).toBeInTheDocument();
    expect(dialog.getByText("8. Nhận laptop", { exact: false })).toBeInTheDocument();
    expect(dialog.getByText("Đăng nhập Outlook và Teams")).toBeInTheDocument();
    expect(dialog.getByText(t.prerequisites)).toBeInTheDocument();
    expect(dialog.getByText("Nhận laptop")).toBeInTheDocument();

    fireEvent.click(dialog.getByRole("button", { name: viMessages.taskSources.view }));
    const viewer = screen.getByRole("dialog", { name: "tài liệu" });
    expect(viewer).toHaveTextContent("Mở: Hướng dẫn ngày 1 / 8. Nhận laptop");
    expect(viewer).toHaveAttribute("data-quote", "Đăng nhập Outlook và Teams");
  });
});
