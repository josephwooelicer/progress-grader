"use client";

import { useState } from "react";
import { RubricDimension, RubricScore } from "@/lib/types";
import RubricDimensionRow from "./RubricDimensionRow";
import AISuggestButton from "./AISuggestButton";
import { fetchRubricScores, createDimension, deleteDimension } from "@/lib/api";

interface Props {
  dimensions: RubricDimension[];
  initialScores: RubricScore[];
  studentId: string;
  projectId: string;
}

export default function RubricPanel({ dimensions: initialDimensions, initialScores, studentId, projectId }: Props) {
  const [scores, setScores] = useState<RubricScore[]>(initialScores);
  const [dimensions, setDimensions] = useState<RubricDimension[]>(initialDimensions);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", scoring_criteria: "", max_score: "5" });
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");
  const [deleting, setDeleting] = useState<string | null>(null);

  async function refreshScores() {
    try {
      const updated = await fetchRubricScores(projectId, studentId);
      setScores(updated);
    } catch {}
  }

  function setField(key: string, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleAddDimension(e: React.FormEvent) {
    e.preventDefault();
    setFormError("");
    setSaving(true);
    try {
      const dim = await createDimension(projectId, {
        name: form.name,
        description: form.description,
        scoring_criteria: form.scoring_criteria,
        max_score: parseInt(form.max_score, 10),
      });
      setDimensions((prev) => [...prev, dim]);
      setForm({ name: "", description: "", scoring_criteria: "", max_score: "5" });
      setShowForm(false);
    } catch (err) {
      setFormError(String(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(dimId: string) {
    setDeleting(dimId);
    try {
      await deleteDimension(projectId, dimId);
      setDimensions((prev) => prev.filter((d) => d.id !== dimId));
      setScores((prev) => prev.filter((s) => s.dimension_id !== dimId));
    } catch (err) {
      alert(String(err));
    } finally {
      setDeleting(null);
    }
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
        <div className="flex gap-2">
          <button
            onClick={() => setShowForm((v) => !v)}
            className="px-3 py-1.5 rounded border border-input text-sm font-medium hover:bg-muted"
          >
            {showForm ? "Cancel" : "+ Add Dimension"}
          </button>
          <AISuggestButton
            projectId={projectId}
            studentId={studentId}
            onComplete={refreshScores}
          />
        </div>
      </div>

      {showForm && (
        <form onSubmit={handleAddDimension} className="mb-4 rounded-lg border bg-card p-4 space-y-3">
          <div className="grid sm:grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-sm font-medium">Dimension Name</label>
              <input
                required
                value={form.name}
                onChange={(e) => setField("name", e.target.value)}
                placeholder="Code quality"
                className="w-full rounded border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium">Max Score</label>
              <input
                required
                type="number"
                min={1}
                max={100}
                value={form.max_score}
                onChange={(e) => setField("max_score", e.target.value)}
                className="w-full rounded border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
              />
            </div>
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium">Description</label>
            <textarea
              required
              value={form.description}
              onChange={(e) => setField("description", e.target.value)}
              rows={2}
              placeholder="What this dimension measures…"
              className="w-full rounded border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring resize-none"
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium">Scoring Criteria</label>
            <textarea
              required
              value={form.scoring_criteria}
              onChange={(e) => setField("scoring_criteria", e.target.value)}
              rows={3}
              placeholder="Score 5 if… Score 3 if… Score 1 if…"
              className="w-full rounded border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring resize-none"
            />
          </div>
          {formError && <p className="text-sm text-destructive">{formError}</p>}
          <button
            type="submit"
            disabled={saving}
            className="px-4 py-2 rounded bg-primary text-primary-foreground text-sm font-medium disabled:opacity-50"
          >
            {saving ? "Adding…" : "Add Dimension"}
          </button>
        </form>
      )}

      <div className="space-y-3">
        {dimensions
          .sort((a, b) => a.display_order - b.display_order)
          .map((dim) => {
            const score = scores.find((s) => s.dimension_id === dim.id);
            return (
              <div key={dim.id} className="relative group">
                <RubricDimensionRow
                  dimension={dim}
                  score={score}
                  studentId={studentId}
                  projectId={projectId}
                  onSaved={refreshScores}
                />
                {!dim.is_mandatory && (
                  <button
                    onClick={() => handleDelete(dim.id)}
                    disabled={deleting === dim.id}
                    title="Delete dimension"
                    className="absolute top-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive text-xs px-1.5 py-0.5 rounded disabled:opacity-30"
                  >
                    {deleting === dim.id ? "…" : "✕"}
                  </button>
                )}
              </div>
            );
          })}
      </div>
    </div>
  );
}
