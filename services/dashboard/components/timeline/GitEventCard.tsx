import { GitCommitEvent, GitBranchCreateEvent, GitBranchDeleteEvent, GitPROpenEvent, GitPRMergeEvent, GitForcePushEvent, TimelineEvent } from "@/lib/types";

const GITEA_URL = process.env.NEXT_PUBLIC_GITEA_URL ?? "";

type GitEvent = GitCommitEvent | GitBranchCreateEvent | GitBranchDeleteEvent | GitPROpenEvent | GitPRMergeEvent | GitForcePushEvent;

export default function GitEventCard({ event }: { event: TimelineEvent }) {
  const e = event as GitEvent;
  const ts = new Date(e.timestamp).toLocaleString();

  if (e.type === "git_commit") {
    return (
      <div className="rounded-lg border bg-card px-4 py-3 text-sm flex gap-3 items-start">
        <span className="text-lg">📝</span>
        <div className="flex-1 min-w-0">
          <p className="font-medium truncate">{e.commit_message || "(no message)"}</p>
          <p className="text-muted-foreground text-xs mt-0.5">
            {GITEA_URL ? (
              <a href={`${GITEA_URL}/commit/${e.commit_sha}`} target="_blank" rel="noreferrer" className="hover:underline font-mono">
                {e.commit_sha.slice(0, 7)}
              </a>
            ) : (
              <span className="font-mono">{e.commit_sha.slice(0, 7)}</span>
            )}
            {" · "}{e.branch_name}{" · "}{ts}
          </p>
        </div>
      </div>
    );
  }

  if (e.type === "git_force_push") {
    return (
      <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm flex gap-3 items-start">
        <span className="text-lg">⚠️</span>
        <div>
          <p className="font-medium text-destructive">Force push</p>
          <p className="text-xs text-muted-foreground mt-0.5">{e.branch_name} · {ts}</p>
        </div>
      </div>
    );
  }

  if (e.type === "git_branch_create") {
    return (
      <div className="rounded-lg border bg-card px-4 py-3 text-sm flex gap-3 items-center">
        <span>🌿</span>
        <span>Branch created: <span className="font-mono font-medium">{e.branch_name}</span></span>
        <span className="ml-auto text-xs text-muted-foreground">{ts}</span>
      </div>
    );
  }

  if (e.type === "git_branch_delete") {
    return (
      <div className="rounded-lg border bg-muted/50 px-4 py-3 text-sm flex gap-3 items-center text-muted-foreground">
        <span>🗑️</span>
        <span>Branch deleted: <span className="font-mono">{e.branch_name}</span></span>
        <span className="ml-auto text-xs">{ts}</span>
      </div>
    );
  }

  if (e.type === "git_pr_open") {
    return (
      <div className="rounded-lg border bg-card px-4 py-3 text-sm flex gap-3 items-start">
        <span className="text-lg">🔀</span>
        <div className="flex-1">
          <p className="font-medium">
            {GITEA_URL ? (
              <a href={`${GITEA_URL}/pulls/${e.pr_number}`} target="_blank" rel="noreferrer" className="hover:underline">
                PR #{e.pr_number}: {e.pr_title}
              </a>
            ) : (
              `PR #${e.pr_number}: ${e.pr_title}`
            )}
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">{ts}</p>
        </div>
      </div>
    );
  }

  if (e.type === "git_pr_merge") {
    return (
      <div className="rounded-lg border border-purple-200 bg-purple-50 px-4 py-3 text-sm flex gap-3 items-center">
        <span>✅</span>
        <span className="font-medium text-purple-800">PR #{e.pr_number} merged: {e.pr_title}</span>
        <span className="ml-auto text-xs text-muted-foreground">{ts}</span>
      </div>
    );
  }

  return null;
}
