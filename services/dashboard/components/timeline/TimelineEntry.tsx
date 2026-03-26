"use client";

import { useState } from "react";
import { TimelineEvent } from "@/lib/types";
import MessageCard from "./MessageCard";
import GitEventCard from "./GitEventCard";
import CommentThread from "./CommentThread";
import FlagButton from "./FlagButton";

interface Props {
  event: TimelineEvent;
  studentId: string;
  projectId: string;
}

export default function TimelineEntry({ event, studentId, projectId }: Props) {
  const [showComments, setShowComments] = useState(false);

  const entryType =
    event.type === "user_message" || event.type === "assistant_message"
      ? "conversation_message"
      : "git_event";

  return (
    <div className="group relative">
      {event.type === "user_message" || event.type === "assistant_message" ? (
        <MessageCard event={event} />
      ) : (
        <GitEventCard event={event} />
      )}

      {/* Hover controls */}
      <div className="mt-1 flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity pl-2">
        <button
          onClick={() => setShowComments((v) => !v)}
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          {showComments ? "Hide comments" : "Comment"}
        </button>
        <FlagButton
          entryType={entryType}
          entryId={event.id}
          studentId={studentId}
          projectId={projectId}
        />
      </div>

      {showComments && (
        <CommentThread
          entryType={entryType}
          entryId={event.id}
          studentId={studentId}
          projectId={projectId}
        />
      )}
    </div>
  );
}
