import { RawTimelineItem } from "@/lib/types";

const GITEA_URL = process.env.NEXT_PUBLIC_GITEA_URL ?? "";

interface Props {
  events: RawTimelineItem[];
}

export default function GitSummary({ events }: Props) {
  const commits = events.filter((e) => e.event_type === "push");
  const forcePushes = events.filter((e) => e.event_type === "force_push");
  const branches = events.filter((e) => e.event_type === "branch_create");
  const prsOpened = events.filter((e) => e.event_type === "pr_open");
  const prsMerged = events.filter((e) => e.event_type === "pr_merge");

  const stats = [
    { label: "Commits", value: commits.length },
    { label: "Force pushes", value: forcePushes.length, warn: forcePushes.length > 0 },
    { label: "Branches created", value: branches.length },
    { label: "PRs opened", value: prsOpened.length },
    { label: "PRs merged", value: prsMerged.length },
  ];

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {stats.map((s) => (
          <div
            key={s.label}
            className={`rounded-lg border px-4 py-3 text-center ${s.warn ? "border-destructive/30 bg-destructive/5" : "bg-card"}`}
          >
            <p className={`text-2xl font-bold ${s.warn ? "text-destructive" : ""}`}>{s.value}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Commits table */}
      {commits.length > 0 && (
        <section>
          <h3 className="font-medium mb-2">Commits</h3>
          <div className="border rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted text-muted-foreground">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">SHA</th>
                  <th className="px-3 py-2 text-left font-medium">Message</th>
                  <th className="px-3 py-2 text-left font-medium">Branch</th>
                  <th className="px-3 py-2 text-left font-medium">Time</th>
                </tr>
              </thead>
              <tbody>
                {commits.map((e) => (
                  <tr key={e.id} className="border-t hover:bg-muted/30">
                    <td className="px-3 py-2 font-mono text-xs">
                      {GITEA_URL && e.commit_sha ? (
                        <a href={`${GITEA_URL}/commit/${e.commit_sha}`} target="_blank" rel="noreferrer" className="hover:underline text-primary">
                          {e.commit_sha?.slice(0, 7)}
                        </a>
                      ) : (
                        e.commit_sha?.slice(0, 7)
                      )}
                    </td>
                    <td className="px-3 py-2 max-w-xs truncate">{e.commit_message}</td>
                    <td className="px-3 py-2 font-mono text-xs">{e.branch_name}</td>
                    <td className="px-3 py-2 text-xs text-muted-foreground whitespace-nowrap">
                      {new Date(e.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* PRs */}
      {prsOpened.length > 0 && (
        <section>
          <h3 className="font-medium mb-2">Pull Requests</h3>
          <div className="space-y-2">
            {prsOpened.map((e) => {
              const merged = prsMerged.some((m) => m.pr_number === e.pr_number);
              return (
                <div key={e.id} className="rounded-lg border bg-card px-4 py-3 text-sm flex items-center gap-3">
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${merged ? "bg-purple-100 text-purple-700" : "bg-green-100 text-green-700"}`}>
                    {merged ? "Merged" : "Open"}
                  </span>
                  {GITEA_URL ? (
                    <a href={`${GITEA_URL}/pulls/${e.pr_number}`} target="_blank" rel="noreferrer" className="hover:underline font-medium flex-1">
                      #{e.pr_number}: {e.pr_title}
                    </a>
                  ) : (
                    <span className="font-medium flex-1">#{e.pr_number}: {e.pr_title}</span>
                  )}
                  <span className="text-xs text-muted-foreground whitespace-nowrap">
                    {new Date(e.created_at).toLocaleString()}
                  </span>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {events.length === 0 && (
        <p className="text-muted-foreground">No Git activity recorded yet.</p>
      )}
    </div>
  );
}
