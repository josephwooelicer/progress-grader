import { ConversationStartEvent } from "@/lib/types";

export default function ConversationStartDivider({ event }: { event: ConversationStartEvent }) {
  const ts = new Date(event.timestamp).toLocaleString();
  return (
    <div className="flex items-center gap-3 my-4 text-xs text-muted-foreground">
      <div className="flex-1 border-t border-dashed border-border" />
      <span className="whitespace-nowrap">
        New conversation · {ts} · {event.model}
      </span>
      <div className="flex-1 border-t border-dashed border-border" />
    </div>
  );
}
