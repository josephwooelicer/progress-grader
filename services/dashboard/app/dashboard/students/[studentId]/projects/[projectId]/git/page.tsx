import { cookies } from "next/headers";
import GitSummary from "@/components/git/GitSummary";
import { RawTimelineItem } from "@/lib/types";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://backend:8000";

async function fetchGitEvents(studentId: string, projectId: string, cookieHeader: string) {
  const res = await fetch(
    `${BACKEND_URL}/api/teacher/students/${studentId}/projects/${projectId}/timeline`,
    { headers: { cookie: cookieHeader }, cache: "no-store" }
  );
  if (!res.ok) return [];
  const data = await res.json();
  return (data.timeline as RawTimelineItem[]).filter((e) => e.type === "git_event");
}

export default async function GitPage({
  params,
}: {
  params: { studentId: string; projectId: string };
}) {
  const cookieStore = cookies();
  const cookieHeader = cookieStore.getAll().map((c) => `${c.name}=${c.value}`).join("; ");
  const events = await fetchGitEvents(params.studentId, params.projectId, cookieHeader);

  return <GitSummary events={events} />;
}
