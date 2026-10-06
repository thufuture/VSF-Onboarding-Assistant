import { fireEvent, render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it } from "vitest";

import viMessages from "../../../messages/vi.json";
import { BarChart } from "./BarChart";
import { ChartCard } from "./ChartCard";
import { DonutChart } from "./DonutChart";
import { LineChart } from "./LineChart";
import { niceTicks, type ChartSeries } from "./chartTheme";

const LABELS = ["29/09", "30/09", "01/10"];
const TWO: ChartSeries[] = [
  { key: "a", label: "Câu hỏi", slot: 1, values: [1, 4, 2] },
  { key: "b", label: "Ticket", slot: 2, values: [0, 1, 1] },
];

function intl(node: React.ReactNode) {
  return render(
    <NextIntlClientProvider locale="vi" messages={viMessages}>
      {node}
    </NextIntlClientProvider>,
  );
}

describe("niceTicks", () => {
  it("mốc trục luôn bắt đầu từ 0, phủ giá trị lớn nhất và là số nguyên với số đếm", () => {
    expect(niceTicks(7, true)).toEqual([0, 2, 4, 6, 8]);
    expect(niceTicks(0, true)).toEqual([0, 1]);
    expect(niceTicks(3, true).every(Number.isInteger)).toBe(true);
    const money = niceTicks(0.0187, false);
    expect(money[0]).toBe(0);
    expect(money[money.length - 1]).toBeGreaterThanOrEqual(0.0187);
  });
});

describe("LineChart", () => {
  it("vẽ mỗi chuỗi một đường 2px, có chú thích màu khi từ hai chuỗi trở lên", () => {
    const { container } = render(<LineChart ariaLabel="Hoạt động" integer labels={LABELS} series={TWO} />);
    expect(container.querySelectorAll("polyline")).toHaveLength(2);
    expect(container.querySelector("polyline")).toHaveAttribute("stroke-width", "2");
    expect(screen.getByText("Câu hỏi")).toBeInTheDocument();
    expect(screen.getByText("Ticket")).toBeInTheDocument();
  });

  it("một chuỗi thì không có khung chú thích (tiêu đề thẻ đã nêu tên)", () => {
    render(<LineChart ariaLabel="Chi phí" labels={LABELS} series={[TWO[0]!]} />);
    expect(screen.queryByText("Câu hỏi")).not.toBeInTheDocument();
  });

  it("phím mũi tên đưa con trỏ qua từng ngày và chú giải hiện đủ giá trị các chuỗi", () => {
    render(
      <LineChart
        ariaLabel="Hoạt động"
        integer
        labels={LABELS}
        series={TWO}
        titles={["Thứ Hai", "Thứ Ba", "Thứ Tư"]}
      />,
    );
    const plot = screen.getByRole("group", { name: "Hoạt động" });
    expect(screen.queryByRole("status")).not.toBeInTheDocument();

    fireEvent.keyDown(plot, { key: "ArrowRight" });
    expect(within(screen.getByRole("status")).getByText("Thứ Hai")).toBeInTheDocument();

    fireEvent.keyDown(plot, { key: "ArrowRight" });
    const tip = within(screen.getByRole("status"));
    expect(tip.getByText("Thứ Ba")).toBeInTheDocument();
    expect(tip.getByText("4")).toBeInTheDocument();
    expect(tip.getByText("1")).toBeInTheDocument();

    fireEvent.keyDown(plot, { key: "ArrowRight" });
    fireEvent.keyDown(plot, { key: "ArrowRight" }); // không vượt quá ngày cuối
    expect(within(screen.getByRole("status")).getByText("Thứ Tư")).toBeInTheDocument();

    fireEvent.blur(plot);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("trỏ chuột vào vùng vẽ hiện chú giải và rời đi thì ẩn", () => {
    render(<LineChart ariaLabel="Hoạt động" integer labels={LABELS} series={TWO} />);
    const plot = screen.getByRole("group", { name: "Hoạt động" });
    fireEvent.pointerMove(plot, { clientX: 300 });
    expect(screen.getByRole("status")).toBeInTheDocument();
    fireEvent.pointerLeave(plot);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("dữ liệu toàn số 0 vẫn vẽ được (đường phẳng ở đáy), không lỗi chia cho 0", () => {
    const { container } = render(
      <LineChart ariaLabel="Trống" labels={LABELS} series={[{ key: "z", label: "Z", slot: 1, values: [0, 0, 0] }]} />,
    );
    expect(container.querySelector("polyline")?.getAttribute("points")).not.toMatch(/NaN|Infinity/);
  });
});

describe("BarChart", () => {
  const categories = [
    { key: "1", label: "Hồ sơ" },
    { key: "2", label: "Đào tạo", extra: [{ label: "Số tài liệu", value: "2" }] },
  ];
  const series: ChartSeries[] = [
    { key: "done", label: "Đã xong", slot: 3, values: [2, 0] },
    { key: "ready", label: "Sẵn sàng", slot: 1, values: [1, 3] },
  ];

  it("xếp chồng: mỗi cột có đúng các đoạn lớn hơn 0 và phần đầu cột được bo tròn", () => {
    const { container } = render(<BarChart ariaLabel="Theo nhóm" categories={categories} integer series={series} stacked />);
    // Hồ sơ: hai đoạn (rect + path đầu cột); Đào tạo: một đoạn (path).
    expect(container.querySelectorAll("svg path")).toHaveLength(2);
    expect(container.querySelectorAll("svg rect")).toHaveLength(1);
  });

  it("chú giải của một cột gồm giá trị các chuỗi và các dòng thêm", () => {
    render(<BarChart ariaLabel="Theo nhóm" categories={categories} integer series={series} stacked />);
    const plot = screen.getByRole("group", { name: "Theo nhóm" });
    fireEvent.keyDown(plot, { key: "ArrowRight" });
    fireEvent.keyDown(plot, { key: "ArrowRight" });
    const tip = within(screen.getByRole("status"));
    expect(tip.getByText("Đào tạo")).toBeInTheDocument();
    expect(tip.getByText("Sẵn sàng")).toBeInTheDocument();
    expect(tip.getByText("3")).toBeInTheDocument();
    expect(tip.getByText("Số tài liệu")).toBeInTheDocument();
  });

  it("đặt cạnh nhau: mỗi chuỗi một thanh riêng", () => {
    const { container } = render(<BarChart ariaLabel="So sánh" categories={categories} series={series} />);
    expect(container.querySelectorAll("svg path")).toHaveLength(3); // 2 + 1 giá trị > 0, giá trị 0 không vẽ
  });
});

describe("DonutChart", () => {
  const slices = [
    { key: "done", label: "Đã xong", value: 3, slot: 3 as const },
    { key: "ready", label: "Sẵn sàng", value: 1, slot: 1 as const },
    { key: "locked", label: "Đang khóa", value: 0, slot: "muted" as const },
  ];

  it("chú thích đủ mọi phần (kể cả phần 0) kèm số và tỷ lệ; chỉ vẽ cung cho phần lớn hơn 0", () => {
    const { container } = render(
      <DonutChart ariaLabel="Trạng thái" centerLabel="hoàn thành" centerValue="75%" slices={slices} />,
    );
    expect(container.querySelectorAll("svg circle")).toHaveLength(3); // vòng nền + 2 cung
    const done = screen.getByText("Đã xong").closest("li")!;
    expect(within(done).getByText("3")).toBeInTheDocument();
    expect(within(done).getByText("75%")).toBeInTheDocument();
    expect(within(screen.getByText("Đang khóa").closest("li")!).getByText("0%")).toBeInTheDocument();
    expect(screen.getByText("75%", { selector: "b" })).toBeInTheDocument(); // số ở giữa vòng
  });

  it("trỏ vào một dòng chú thích thì giữa vòng đổi sang phần đó, rời đi thì trở lại tổng", () => {
    render(<DonutChart ariaLabel="Trạng thái" centerLabel="hoàn thành" centerValue="75%" slices={slices} />);
    const item = screen.getByText("Sẵn sàng").closest("li")!;
    fireEvent.pointerEnter(item);
    expect(screen.getByText("Sẵn sàng · 25%")).toBeInTheDocument();
    fireEvent.pointerLeave(item);
    expect(screen.queryByText("Sẵn sàng · 25%")).not.toBeInTheDocument();
    expect(screen.getByText("hoàn thành")).toBeInTheDocument();
  });

  it("tổng bằng 0 chỉ có vòng nền, không lỗi", () => {
    const { container } = render(
      <DonutChart
        ariaLabel="Trống"
        centerLabel="USD"
        centerValue="0"
        slices={[{ key: "none", label: "Chưa có", value: 0, slot: "muted" }]}
      />,
    );
    expect(container.querySelectorAll("svg circle")).toHaveLength(1);
  });
});

describe("ChartCard", () => {
  it("chuyển giữa biểu đồ và bảng số liệu cùng dữ liệu", () => {
    intl(
      <ChartCard
        subtitle="Mô tả"
        table={{ head: ["Ngày", "Số lượng"], rows: [["29/09", 1], ["30/09", 4]] }}
        title="Hoạt động"
      >
        <div>nội dung biểu đồ</div>
      </ChartCard>,
    );
    expect(screen.getByText("nội dung biểu đồ")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Xem dạng bảng/ }));
    expect(screen.queryByText("nội dung biểu đồ")).not.toBeInTheDocument();
    const table = within(screen.getByRole("table"));
    expect(table.getByText("30/09")).toBeInTheDocument();
    expect(table.getByText("4")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Xem dạng biểu đồ/ }));
    expect(screen.getByText("nội dung biểu đồ")).toBeInTheDocument();
  });

  it("bảng rỗng hiện thông báo chưa có dữ liệu", () => {
    intl(
      <ChartCard table={{ head: ["Lượt"], rows: [] }} title="Lượt chạy">
        <div />
      </ChartCard>,
    );
    fireEvent.click(screen.getByRole("button", { name: /Xem dạng bảng/ }));
    expect(screen.getByText("Chưa có dữ liệu trong khoảng này.")).toBeInTheDocument();
  });
});
