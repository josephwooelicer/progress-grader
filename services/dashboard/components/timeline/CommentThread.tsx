"use client";

import { useState } from "react";
import { postComment } from "@/lib/api";

interface Props {
  entryType: string;
  entryId: string;
  studentId: string;
  projectId: string;
}

interface Comment {
  id: string;
  content: string;
  created_at: string;
}

export default function CommentThread({ entryType, entryId, studentId, projectId }: Props) {
  const [comments, setComments] = useState<Comment[]>([]);
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setSaving(true);
    try {
      const result = await postComment({ student_id: studentId, project_id: projectId, entry_type: entryType, entry_id: entryId, content: text.trim() });
      setComments((prev) => [...prev, { id: result.id, content: text.trim(), created_at: new Date().toISOString() }]);
      setText("");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="ml-4 mt-2 border-l-2 border-border pl-4 space-y-2">
      {comments.map((c) => (
        <div key={c.id} className="text-sm bg-muted rounded px-3 py-2">
          <p>{c.content}</p>
          <p className="text-xs text-muted-foreground mt-1">
            {new Date(c.created_at).toLocaleString()}
          </p>
        </div>
      ))}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Add a comment…"
          className="flex-1 text-sm rounded border border-input bg-background px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-ring"
        />
        <button
          type="submit"
          disabled={saving || !text.trim()}
          className="text-sm px-3 py-1.5 rounded bg-primary text-primary-foreground disabled:opacity-50"
        >
          {saving ? "…" : "Post"}
        </button>
      </form>
    </div>
  );
}
