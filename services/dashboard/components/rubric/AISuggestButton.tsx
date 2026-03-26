"use client";

import { useState } from "react";
import { triggerAISuggest } from "@/lib/api";

interface Props {
  projectId: string;
  studentId: string;
  onComplete: () => void;
}

export default function AISuggestButton({ projectId, studentId, onComplete }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleClick() {
    setLoading(true);
    setError("");
    try {
      await triggerAISuggest(projectId, studentId);
      onComplete();
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        onClick={handleClick}
        disabled={loading}
        className="px-4 py-2 rounded-md bg-secondary text-secondary-foreground text-sm font-medium hover:opacity-90 disabled:opacity-50 flex items-center gap-2"
      >
        {loading && (
          <span className="inline-block w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
        )}
        {loading ? "Running AI grading…" : "✨ Run AI Grading"}
      </button>
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}
