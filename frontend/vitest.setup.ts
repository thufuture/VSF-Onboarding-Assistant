import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

import viMessages from "./messages/vi.json";

/** Tra một khóa trong vi.json theo namespace, thay `{tên}` bằng giá trị; thiếu khóa thì trả lại chính khóa. */
function translate(namespace: string | undefined, key: string, values?: Record<string, unknown>) {
  const path = [...(namespace ? namespace.split(".") : []), ...key.split(".")];
  const template = path.reduce<unknown>((current, segment) => {
    if (!current || typeof current !== "object") return undefined;
    return (current as Record<string, unknown>)[segment];
  }, viMessages);
  if (typeof template !== "string") return key;
  return Object.entries(values ?? {}).reduce(
    (result, [name, value]) => result.replaceAll(`{${name}}`, String(value)),
    template,
  );
}

vi.mock("next-intl", () => ({
  NextIntlClientProvider: ({ children }: { children: unknown }) => children,
  useLocale: () => "vi",
  useTranslations: (namespace?: string) => (key: string, values?: Record<string, unknown>) =>
    translate(namespace, key, values),
}));
