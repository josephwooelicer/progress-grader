"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { createCourse } from "@/lib/api";
import { Course } from "@/lib/types";

export default function DashboardPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/api/backend/api/teacher/courses")
      .then((r) => r.json())
      .then((d) => setCourses(d.courses ?? []));
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      const course = await createCourse({ name, slug });
      setCourses((prev) => [...prev, course as unknown as Course]);
      setName("");
      setSlug("");
      setShowForm(false);
    } catch (err) {
      setError(String(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Courses</h1>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:opacity-90"
        >
          {showForm ? "Cancel" : "+ New Course"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="mb-6 rounded-lg border bg-card p-4 space-y-3">
          <div className="grid sm:grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-sm font-medium">Name</label>
              <input
                required
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  if (!slug) setSlug(e.target.value.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, ""));
                }}
                placeholder="Web Engineering 101"
                className="w-full rounded border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium">Slug</label>
              <input
                required
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                placeholder="web-engineering-101"
                className="w-full rounded border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring font-mono"
              />
            </div>
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <button
            type="submit"
            disabled={saving}
            className="px-4 py-2 rounded bg-primary text-primary-foreground text-sm font-medium disabled:opacity-50"
          >
            {saving ? "Creating…" : "Create Course"}
          </button>
        </form>
      )}

      {courses.length === 0 ? (
        <p className="text-muted-foreground">No courses yet. Create one above.</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {courses.map((course) => (
            <Link
              key={course.id}
              href={`/dashboard/courses/${course.id}`}
              className="block rounded-lg border bg-card p-5 hover:shadow-sm transition-shadow"
            >
              <p className="font-medium">{course.name}</p>
              <p className="text-sm text-muted-foreground mt-1 font-mono">{course.slug}</p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
