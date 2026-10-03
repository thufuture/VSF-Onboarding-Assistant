import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { JourneyRoad, type RoadItem } from "./JourneyRoad";

const items = (count: number): RoadItem[] =>
  Array.from({ length: count }, (_, i) => ({ id: i + 1, title: `Việc ${i + 1}`, group: "PROFILE" as const, pill: "Nháp", chips: [] }));

function canvasWidth(count: number): number {
  const { container } = render(
    <JourneyRoad
      actionsFor={() => []}
      items={items(count)}
      labels={{ start: "Bắt đầu", finish: "Kết thúc", taskNo: (n) => `Việc ${n}` }}
      onOpen={() => undefined}
    />,
  );
  const canvas = container.querySelector<HTMLElement>('div[style*="min-width"]');
  return Number.parseInt(canvas?.style.minWidth ?? "0", 10);
}

describe("Roadmap dùng chung", () => {
  it("đủ rộng để hai thẻ cùng hàng (cách nhau hai bước nút) còn hở ít nhất 24px", () => {
    for (const count of [3, 6, 12, 20]) {
      const width = canvasWidth(count);
      // Nút rải từ 6% tới 94% qua (n+1) bước; thẻ rộng 196 và cùng hàng thì cách nhau 2 bước.
      const stepPx = (width * 0.88) / (count + 1);
      expect(2 * stepPx - 196, `${count} việc, canvas ${width}px`).toBeGreaterThanOrEqual(24);
    }
  });

  it("ít việc thì giữ chiều rộng tối thiểu 820px", () => {
    expect(canvasWidth(2)).toBe(820);
  });
});
