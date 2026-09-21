import { useTranslations } from "next-intl";

import { FeatureCards } from "@/features/landing/FeatureCards";
import { Footer } from "@/features/landing/Footer";
import { Hero } from "@/features/landing/Hero";
import { Navbar } from "@/features/landing/Navbar";
import { Steps } from "@/features/landing/Steps";

// Landing tĩnh, chỉ tiếng Việt, không gọi API (landing-page-plan.md). Nút "Bắt đầu hỏi" dẫn tới /vi/login.
export default function HomePage() {
  const t = useTranslations("landing");

  return (
    <>
      <a
        href="#main"
        className="bg-surface text-ink border-border sr-only rounded-md border px-3 py-2 focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-20"
      >
        {t("skipLink")}
      </a>
      <Navbar />
      <main id="main">
        <Hero />
        <Steps />
        <FeatureCards />
      </main>
      <Footer />
    </>
  );
}
