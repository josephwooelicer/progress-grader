"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { createProject } from "@/lib/api";

interface StudentRow {
  id: string;
  name: string;
  email: string;
  consented: boolean;
  project_id: string;
  project_name: string;
}

export default function CoursePage({ params }: { params: { courseId: string } }) {
  const { courseId } = params;
  const [students, setStudents] = useState<StudentRow[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", slug: "", description: "", model: "", api_key: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`/api/backend/api/teacher/courses/${courseId}/students`)
      .then((r) => r.json())
      .then((d) => setStudents(d.students ?? []));
  }, [courseId]);

  function setField(key: string, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      await createProject(courseId, {
        name: form.name,
        slug: form.slug,
        description: form.description || undefined,
        model: form.model || undefined,
        api_key: form.api_key || undefined,
      });
      setShowForm(false);
      setForm({ name: "", slug: "", description: "", model: "", api_key: "" });
      // Re-fetch students (project may now show up)
      const res = await fetch(`/api/backend/api/teacher/courses/${courseId}/students`);
      const d = await res.json();
      setStudents(d.students ?? []);
    } catch (err) {
      setError(String(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Students</h1>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:opacity-90"
        >
          {showForm ? "Cancel" : "+ New Project"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="mb-6 rounded-lg border bg-card p-4 space-y-3">
          <div className="grid sm:grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-sm font-medium">Project Name</label>
              <input required value={form.name} onChange={(e) => { setField("name", e.target.value); if (!form.slug) setField("slug", e.target.value.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "")); }} placeholder="Final Project" className="w-full rounded border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring" />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium">Slug</label>
              <input required value={form.slug} onChange={(e) => setField("slug", e.target.value)} placeholder="final-project" className="w-full rounded border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring font-mono" />
            </div>
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium">Description <span className="text-muted-foreground">(optional)</span></label>
            <textarea value={form.description} onChange={(e) => setField("description", e.target.value)} rows={2} placeholder="Build a REST API…" className="w-full rounded border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring resize-none" />
          </div>
          <div className="grid sm:grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-sm font-medium">AI Model <span className="text-muted-foreground">(optional, overrides platform default)</span></label>
              <input value={form.model} onChange={(e) => setField("model", e.target.value)} placeholder="gpt-4o" className="w-full rounded border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring font-mono" />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium">API Key <span className="text-muted-foreground">(optional, stored encrypted)</span></label>
              <input type="password" value={form.api_key} onChange={(e) => setField("api_key", e.target.value)} placeholder="sk-…" className="w-full rounded border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring" />
            </div>
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <button type="submit" disabled={saving} className="px-4 py-2 rounded bg-primary text-primary-foreground text-sm font-medium disabled:opacity-50">
            {saving ? "Creating…" : "Create Project"}
          </button>
          <p className="text-xs text-muted-foreground">7 mandatory rubric dimensions will be added automatically.</p>
        </form>
      )}

      {students.length === 0 ? (
        <p className="text-muted-foreground">No students yet — they will appear once workspaces are created.</p>
      ) : (
        <div className="border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted text-muted-foreground">
              <tr>
                <th className="px-4 py-3 text-left font-medium">Student</th>
                <th className="px-4 py-3 text-left font-medium">Project</th>
                <th className="px-4 py-3 text-left font-medium">Consent</th>
                <th className="px-4 py-3 text-left font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {students.map((s) => (
                <tr key={`${s.id}-${s.project_id}`} className="border-t hover:bg-muted/30">
                  <td className="px-4 py-3">
                    <p className="font-medium">{s.name}</p>
                    <p className="text-muted-foreground">{s.email}</p>
                  </td>
                  <td className="px-4 py-3">{s.project_name}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${s.consented ? "bg-green-100 text-green-800" : "bg-yellow-100 text-yellow-800"}`}>
                      {s.consented ? "Consented" : "No consent"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {s.consented ? (
                      <div className="flex gap-3">
                        <Link href={`/dashboard/students/${s.id}/projects/${s.project_id}/timeline`} className="text-primary hover:underline">Timeline</Link>
                        <Link href={`/dashboard/students/${s.id}/projects/${s.project_id}/rubric`} className="text-primary hover:underline">Rubric</Link>
                        <Link href={`/dashboard/students/${s.id}/projects/${s.project_id}/git`} className="text-primary hover:underline">Git</Link>
                      </div>
                    ) : (
                      <span className="text-muted-foreground text-xs">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
