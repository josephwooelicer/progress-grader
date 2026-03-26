import { cookies } from "next/headers";
import TimelineList from "@/components/timeline/TimelineList";
import { normaliseTimelineServer } from "@/lib/timeline-server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://backend:8000";

async function fetchTimeline(studentId: string, projectId: string, cookieHeader: string) {
  const res = await fetch(
    `${BACKEND_URL}/api/teacher/students/${studentId}/projects/${projectId}/timeline`,
    { headers: { cookie: cookieHeader }, cache: "no-store" }
  );
  if (res.status === 403) return { noConsent: true, events: [] };
  if (!res.ok) return { noConsent: false, events: [] };
  const data = await res.json();
  return { noConsent: false, events: normaliseTimelineServer(data.timeline ?? []) };
}

export default async function TimelinePage({
  params,
}: {
  params: { studentId: string; projectId: string };
}) {
  const cookieStore = cookies();
  const cookieHeader = cookieStore.getAll().map((c) => `${c.name}=${c.value}`).join("; ");
  const { noConsent, events } = await fetchTimeline(
    params.studentId,
    params.projectId,
    cookieHeader
  );

  if (noConsent) {
    return (
      <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-6 text-center">
        <p className="font-medium text-yellow-800">No consent on file</p>
        <p className="text-sm text-yellow-700 mt-1">
          This student has not consented to data collection for this project.
        </p>
      </div>
    );
  }

  return (
    <TimelineList
      events={events}
      studentId={params.studentId}
      projectId={params.projectId}
    />
  );
}
