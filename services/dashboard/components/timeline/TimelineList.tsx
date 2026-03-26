"use client";

import { useState } from "react";
import { TimelineEvent } from "@/lib/types";
import TimelineEntry from "./TimelineEntry";
import ConversationStartDivider from "./ConversationStartDivider";

interface Props {
  events: TimelineEvent[];
  studentId: string;
  projectId: string;
}

export default function TimelineList({ events, studentId, projectId }: Props) {
  const [filter, setFilter] = useState<"all" | "ai" | "git">("all");

  const filtered = events.filter((e) => {
    if (filter === "ai") return e.type === "user_message" || e.type === "assistant_message" || e.type === "conversation_start";
    if (filter === "git") return e.type.startsWith("git_");
    return true;
  });

  if (events.length === 0) {
    return <p className="text-muted-foreground">No activity yet for this student.</p>;
  }

  return (
    <div>
      {/* Filter bar */}
      <div className="flex gap-2 mb-5">
        {(["all", "ai", "git"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
              filter === f
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:bg-muted/70"
            }`}
          >
            {f === "all" ? "All" : f === "ai" ? "AI Chat" : "Git"}
          </button>
        ))}
        <span className="ml-auto text-xs text-muted-foreground self-center">
          {filtered.length} events
        </span>
      </div>

      <div className="space-y-2">
        {filtered.map((event) => {
          if (event.type === "conversation_start") {
            return <ConversationStartDivider key={event.id} event={event} />;
          }
          return (
            <TimelineEntry
              key={event.id}
              event={event}
              studentId={studentId}
              projectId={projectId}
            />
          );
        })}
      </div>
    </div>
  );
}
