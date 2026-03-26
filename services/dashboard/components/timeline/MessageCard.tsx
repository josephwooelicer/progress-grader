import { UserMessageEvent, AssistantMessageEvent } from "@/lib/types";

type Props = { event: UserMessageEvent | AssistantMessageEvent };

export default function MessageCard({ event }: Props) {
  const isUser = event.type === "user_message";
  const ts = new Date(event.timestamp).toLocaleTimeString();
  const tokens = isUser
    ? event.input_tokens != null ? `${event.input_tokens} in` : null
    : event.output_tokens != null ? `${event.output_tokens} out` : null;

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[75%] rounded-xl px-4 py-2.5 text-sm ${
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted border border-border"
        }`}
      >
        <p className="whitespace-pre-wrap break-words">{event.content}</p>
        <div className={`flex gap-2 mt-1 text-xs ${isUser ? "text-primary-foreground/70 justify-end" : "text-muted-foreground"}`}>
          <span>{ts}</span>
          {tokens && <span>· {tokens}</span>}
        </div>
      </div>
    </div>
  );
}
