import { Suspense } from "react";

import { VigaPage } from "@/features/viga/VigaPage";

export default function MeVigaRoute() {
  // `useSearchParams` (mở đúng cuộc trò chuyện từ ngăn Viga) cần Suspense khi trang được dựng sẵn.
  return (
    <Suspense>
      <VigaPage />
    </Suspense>
  );
}
