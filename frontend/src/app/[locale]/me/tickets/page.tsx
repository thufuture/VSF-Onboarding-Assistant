import { Suspense } from "react";

import { EmployeeTicketsPage } from "@/features/portal-employee/TicketsPage";

export default function MeTicketsRoute() {
  // `useSearchParams` (mở đúng ticket từ thông báo) cần Suspense khi trang được dựng sẵn.
  return (
    <Suspense>
      <EmployeeTicketsPage />
    </Suspense>
  );
}
