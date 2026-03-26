import { RawTimelineItem, TimelineEvent, RubricDimension, RubricScore, Course, Project } from "./types";

const BASE = "/api/backend";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

// ── Timeline ──────────────────────────────────────────────────────────────────

export async function fetchTimeline(
  studentId: string,
  projectId: string
): Promise<TimelineEvent[]> {
  const data = await apiFetch<{ timeline: RawTimelineItem[] }>(
    `/api/teacher/students/${studentId}/projects/${projectId}/timeline`
  );
  return normaliseTimeline(data.timeline);
}

/**
 * Convert raw backend items into typed TimelineEvents.
 * Inserts ConversationStart dividers when conversation_id changes.
 */
function normaliseTimeline(items: RawTimelineItem[]): TimelineEvent[] {
  const events: TimelineEvent[] = [];
  let lastConvId: string | null = null;

  for (const item of items) {
    if (item.type === "conversation_message") {
      const convId = item.conversation_id!;

      // Insert divider at conversation boundary
      if (convId !== lastConvId) {
        events.push({
          type: "conversation_start",
          id: convId,
          conversation_id: convId,
          model: item.model ?? "unknown",
          timestamp: item.created_at,
        });
        lastConvId = convId;
      }

      if (item.role === "user") {
        events.push({
          type: "user_message",
          id: item.id,
          conversation_id: convId,
          content: item.content ?? "",
          input_tokens: item.input_tokens ?? null,
          timestamp: item.created_at,
        });
      } else {
        events.push({
          type: "assistant_message",
          id: item.id,
          conversation_id: convId,
          content: item.content ?? "",
          output_tokens: item.output_tokens ?? null,
          timestamp: item.created_at,
        });
      }
    } else {
      // git_event
      const etype = item.event_type ?? "";
      if (etype === "push") {
        events.push({
          type: "git_commit",
          id: item.id,
          commit_sha: item.commit_sha ?? "",
          commit_message: item.commit_message ?? "",
          branch_name: item.branch_name ?? "",
          forced: false,
          timestamp: item.created_at,
        });
      } else if (etype === "force_push") {
        events.push({
          type: "git_force_push",
          id: item.id,
          commit_sha: item.commit_sha ?? null,
          branch_name: item.branch_name ?? "",
          timestamp: item.created_at,
        });
      } else if (etype === "branch_create") {
        events.push({
          type: "git_branch_create",
          id: item.id,
          branch_name: item.branch_name ?? "",
          timestamp: item.created_at,
        });
      } else if (etype === "branch_delete") {
        events.push({
          type: "git_branch_delete",
          id: item.id,
          branch_name: item.branch_name ?? "",
          timestamp: item.created_at,
        });
      } else if (etype === "pr_open") {
        events.push({
          type: "git_pr_open",
          id: item.id,
          pr_number: item.pr_number ?? 0,
          pr_title: item.pr_title ?? "",
          branch_name: item.branch_name ?? null,
          timestamp: item.created_at,
        });
      } else if (etype === "pr_merge") {
        events.push({
          type: "git_pr_merge",
          id: item.id,
          pr_number: item.pr_number ?? 0,
          pr_title: item.pr_title ?? "",
          timestamp: item.created_at,
        });
      }
    }
  }

  return events;
}

// ── Comments ──────────────────────────────────────────────────────────────────

export async function postComment(body: {
  student_id: string;
  project_id: string;
  entry_type: string;
  entry_id: string;
  content: string;
}): Promise<{ id: string }> {
  return apiFetch("/api/teacher/comments", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ── Flags ─────────────────────────────────────────────────────────────────────

export async function toggleFlag(body: {
  student_id: string;
  project_id: string;
  entry_type: string;
  entry_id: string;
  note?: string;
}): Promise<{ flagged: boolean }> {
  return apiFetch("/api/teacher/flags/toggle", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ── Rubric ────────────────────────────────────────────────────────────────────

export async function fetchRubricDimensions(projectId: string): Promise<RubricDimension[]> {
  const data = await apiFetch<{ dimensions: RubricDimension[] }>(
    `/api/teacher/projects/${projectId}/rubric/dimensions`
  );
  return data.dimensions;
}

export async function fetchRubricScores(
  projectId: string,
  studentId: string
): Promise<RubricScore[]> {
  const data = await apiFetch<{ scores: RubricScore[] }>(
    `/api/teacher/projects/${projectId}/rubric/scores?student_id=${studentId}`
  );
  return data.scores;
}

export async function triggerAISuggest(
  projectId: string,
  studentId: string
): Promise<{ suggestions: Array<{ dimension_name: string; score: number; justification: string }> }> {
  return apiFetch(
    `/api/teacher/projects/${projectId}/rubric/ai-suggest?student_id=${studentId}`,
    { method: "POST" }
  );
}

export async function saveScore(
  projectId: string,
  body: {
    student_id: string;
    dimension_id: string;
    confirmed_score: number;
    confirmed_justification?: string;
  }
): Promise<{ ok: boolean }> {
  return apiFetch(`/api/teacher/projects/${projectId}/rubric/grade`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// ── Setup ─────────────────────────────────────────────────────────────────────

export async function createCourse(body: { name: string; slug: string }): Promise<Course> {
  return apiFetch("/api/teacher/courses", { method: "POST", body: JSON.stringify(body) });
}

export async function createProject(
  courseId: string,
  body: { name: string; slug: string; description?: string; provider?: string; model?: string; api_key?: string }
): Promise<Project> {
  return apiFetch(`/api/teacher/courses/${courseId}/projects`, { method: "POST", body: JSON.stringify(body) });
}

export async function createDimension(
  projectId: string,
  body: { name: string; description: string; scoring_criteria: string; max_score: number }
): Promise<RubricDimension> {
  return apiFetch(`/api/teacher/projects/${projectId}/rubric/dimensions`, { method: "POST", body: JSON.stringify(body) });
}

export async function deleteDimension(projectId: string, dimensionId: string): Promise<void> {
  await apiFetch(`/api/teacher/projects/${projectId}/rubric/dimensions/${dimensionId}`, { method: "DELETE" });
}
