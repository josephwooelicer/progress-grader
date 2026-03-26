"use client";

import { useState } from "react";
import { RubricDimension, RubricScore } from "@/lib/types";
import { saveScore } from "@/lib/api";

interface Props {
  dimension: RubricDimension;
  score: RubricScore | undefined;
  studentId: string;
  projectId: string;
  onSaved: () => void;
}

export default function RubricDimensionRow({ dimension, score, studentId, projectId, onSaved }: Props) {
  const [expanded, setExpanded] = useState(false);
  const [value, setValue] = useState<number>(score?.confirmed_score ?? score?.suggested_score ?? 0);
  const [justification, setJustification] = useState(score?.confirmed_justification ?? score?.suggested_justification ?? "");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  async function handleConfirm() {
    setSaving(true);
    try {
      await saveScore(projectId, {
        student_id: studentId,
        dimension_id: dimension.id,
        confirmed_score: value,
        confirmed_justification: justification || undefined,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
      onSaved();
    } finally {
      setSaving(false);
    }
  }

  const isConfirmed = score?.confirmed_score != null;
  const hasSuggestion = score?.suggested_score != null;

  return (
    <div className={`rounded-lg border bg-card ${isConfirmed ? "border-green-200" : ""}`}>
      <div className="px-4 py-3">
        <div className="flex items-start gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium text-sm">{dimension.name}</span>
              {dimension.is_mandatory && (
                <span className="text-xs bg-muted text-muted-foreground px-1.5 py-0.5 rounded">mandatory</span>
              )}
              {isConfirmed && (
                <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded">confirmed</span>
              )}
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">{dimension.description}</p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {hasSuggestion && !isConfirmed && (
              <span className="text-xs text-muted-foreground">AI: {score!.suggested_score}/{dimension.max_score}</span>
            )}
            <input
              type="number"
              min={0}
              max={dimension.max_score}
              value={value}
              onChange={(e) => setValue(Number(e.target.value))}
              className="w-16 rounded border border-input bg-background px-2 py-1 text-sm text-center focus:outline-none focus:ring-1 focus:ring-ring"
            />
            <span className="text-sm text-muted-foreground">/ {dimension.max_score}</span>
            <button
              onClick={handleConfirm}
              disabled={saving}
              className="text-xs px-3 py-1.5 rounded bg-primary text-primary-foreground hover:opacity-90 disabled:opacity-50"
            >
              {saved ? "Saved ✓" : saving ? "…" : "Confirm"}
            </button>
          </div>
        </div>

        {/* AI justification */}
        {hasSuggestion && score?.suggested_justification && (
          <div className="mt-2 text-xs bg-blue-50 border border-blue-100 rounded px-3 py-2 text-blue-800">
            <span className="font-medium">AI: </span>{score.suggested_justification}
          </div>
        )}

        {/* Criteria toggle */}
        <button
          onClick={() => setExpanded((v) => !v)}
          className="mt-2 text-xs text-muted-foreground hover:text-foreground"
        >
          {expanded ? "Hide criteria" : "View scoring criteria"}
        </button>
        {expanded && (
          <p className="mt-1 text-xs text-muted-foreground bg-muted rounded px-3 py-2 whitespace-pre-wrap">
            {dimension.scoring_criteria}
          </p>
        )}

        {/* Teacher annotation */}
        <textarea
          value={justification}
          onChange={(e) => setJustification(e.target.value)}
          placeholder="Annotation (optional)…"
          rows={2}
          className="mt-2 w-full text-xs rounded border border-input bg-background px-3 py-2 focus:outline-none focus:ring-1 focus:ring-ring resize-none"
        />
      </div>
    </div>
  );
}
