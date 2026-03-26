"use client";

import { useState } from "react";
import { RubricDimension, RubricScore } from "@/lib/types";
import RubricDimensionRow from "./RubricDimensionRow";
import AISuggestButton from "./AISuggestButton";
import { fetchRubricScores } from "@/lib/api";

interface Props {
  dimensions: RubricDimension[];
  initialScores: RubricScore[];
  studentId: string;
  projectId: string;
}

export default function RubricPanel({ dimensions, initialScores, studentId, projectId }: Props) {
  const [scores, setScores] = useState<RubricScore[]>(initialScores);

  async function refreshScores() {
    try {
      const updated = await fetchRubricScores(projectId, studentId);
      setScores(updated);
    } catch {}
  }

  const maxTotal = dimensions.reduce((sum, d) => sum + d.max_score, 0);
  const confirmedTotal = scores.reduce((sum, s) => sum + (s.confirmed_score ?? 0), 0);
  const confirmedCount = scores.filter((s) => s.confirmed_score != null).length;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold">Rubric Scoring</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            {confirmedCount}/{dimensions.length} dimensions confirmed · Total: {confirmedTotal}/{maxTotal}
          </p>
        </div>
        <AISuggestButton
          projectId={projectId}
          studentId={studentId}
          onComplete={refreshScores}
        />
      </div>

      <div className="space-y-3">
        {dimensions
          .sort((a, b) => a.display_order - b.display_order)
          .map((dim) => {
            const score = scores.find((s) => s.dimension_id === dim.id);
            return (
              <RubricDimensionRow
                key={dim.id}
                dimension={dim}
                score={score}
                studentId={studentId}
                projectId={projectId}
                onSaved={refreshScores}
              />
            );
          })}
      </div>
    </div>
  );
}
