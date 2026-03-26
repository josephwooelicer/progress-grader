"use client";

import { useState } from "react";
import { toggleFlag } from "@/lib/api";

interface Props {
  entryType: string;
  entryId: string;
  studentId: string;
  projectId: string;
  initialFlagged?: boolean;
}

export default function FlagButton({ entryType, entryId, studentId, projectId, initialFlagged = false }: Props) {
  const [flagged, setFlagged] = useState(initialFlagged);
  const [loading, setLoading] = useState(false);

  async function handleToggle() {
    setLoading(true);
    try {
      const result = await toggleFlag({ entry_type: entryType, entry_id: entryId, student_id: studentId, project_id: projectId });
      setFlagged(result.flagged);
    } finally {
      setLoading(false);
    }
  }

  return (
    <button
      onClick={handleToggle}
      disabled={loading}
      title={flagged ? "Remove flag" : "Flag this entry"}
      className={`text-sm transition-colors ${flagged ? "text-yellow-500 hover:text-yellow-600" : "text-muted-foreground hover:text-yellow-500"}`}
    >
      {flagged ? "★" : "☆"}
    </button>
  );
}
