import { RawTimelineItem, TimelineEvent } from "./types";

export function normaliseTimelineServer(items: RawTimelineItem[]): TimelineEvent[] {
  const events: TimelineEvent[] = [];
  let lastConvId: string | null = null;

  for (const item of items) {
    if (item.type === "conversation_message") {
      const convId = item.conversation_id!;
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
      const etype = item.event_type ?? "";
      if (etype === "push") {
        events.push({ type: "git_commit", id: item.id, commit_sha: item.commit_sha ?? "", commit_message: item.commit_message ?? "", branch_name: item.branch_name ?? "", forced: false, timestamp: item.created_at });
      } else if (etype === "force_push") {
        events.push({ type: "git_force_push", id: item.id, commit_sha: item.commit_sha ?? null, branch_name: item.branch_name ?? "", timestamp: item.created_at });
      } else if (etype === "branch_create") {
        events.push({ type: "git_branch_create", id: item.id, branch_name: item.branch_name ?? "", timestamp: item.created_at });
      } else if (etype === "branch_delete") {
        events.push({ type: "git_branch_delete", id: item.id, branch_name: item.branch_name ?? "", timestamp: item.created_at });
      } else if (etype === "pr_open") {
        events.push({ type: "git_pr_open", id: item.id, pr_number: item.pr_number ?? 0, pr_title: item.pr_title ?? "", branch_name: item.branch_name ?? null, timestamp: item.created_at });
      } else if (etype === "pr_merge") {
        events.push({ type: "git_pr_merge", id: item.id, pr_number: item.pr_number ?? 0, pr_title: item.pr_title ?? "", timestamp: item.created_at });
      }
    }
  }

  return events;
}
