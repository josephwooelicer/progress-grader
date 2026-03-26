import { cookies } from "next/headers";
import RubricPanel from "@/components/rubric/RubricPanel";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://backend:8000";

async function fetchRubricData(projectId: string, studentId: string, cookieHeader: string) {
  const [dimsRes, scoresRes] = await Promise.all([
    fetch(`${BACKEND_URL}/api/teacher/projects/${projectId}/rubric/dimensions`, {
      headers: { cookie: cookieHeader },
      cache: "no-store",
    }),
    fetch(
      `${BACKEND_URL}/api/teacher/projects/${projectId}/rubric/scores?student_id=${studentId}`,
      { headers: { cookie: cookieHeader }, cache: "no-store" }
    ),
  ]);

  const dimensions = dimsRes.ok ? (await dimsRes.json()).dimensions ?? [] : [];
  const scores = scoresRes.ok ? (await scoresRes.json()).scores ?? [] : [];
  return { dimensions, scores };
}

export default async function RubricPage({
  params,
}: {
  params: { studentId: string; projectId: string };
}) {
  const cookieStore = cookies();
  const cookieHeader = cookieStore.getAll().map((c) => `${c.name}=${c.value}`).join("; ");
  const { dimensions, scores } = await fetchRubricData(
    params.projectId,
    params.studentId,
    cookieHeader
  );

  return (
    <RubricPanel
      dimensions={dimensions}
      initialScores={scores}
      studentId={params.studentId}
      projectId={params.projectId}
    />
  );
}
