import { EmployeeTaskPage } from "@/features/portal-employee/TaskPage";

export default async function MeTaskRoute({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <EmployeeTaskPage taskId={Number(id)} />;
}
