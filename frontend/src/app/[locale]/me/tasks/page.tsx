import { Suspense } from "react";

import { EmployeeTasksPage } from "@/features/portal-employee/TasksPage";

// `useSearchParams` (ngày và task đang mở nằm ở địa chỉ) cần ranh giới Suspense khi dựng tĩnh.
export default function MeTasksRoute() {
  return (
    <Suspense fallback={null}>
      <EmployeeTasksPage />
    </Suspense>
  );
}
