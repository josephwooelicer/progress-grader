import Link from "next/link";
import { cookies } from "next/headers";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://backend:8000";

interface Course {
  id: string;
  name: string;
  slug: string;
  created_at: string;
}

async function fetchCourses(cookieHeader: string): Promise<Course[]> {
  try {
    const res = await fetch(`${BACKEND_URL}/api/teacher/courses`, {
      headers: { cookie: cookieHeader },
      cache: "no-store",
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.courses ?? [];
  } catch {
    return [];
  }
}

export default async function DashboardPage() {
  const cookieStore = cookies();
  const cookieHeader = cookieStore.getAll().map((c) => `${c.name}=${c.value}`).join("; ");
  const courses = await fetchCourses(cookieHeader);

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-6">Courses</h1>
      {courses.length === 0 ? (
        <p className="text-muted-foreground">No courses found.</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {courses.map((course) => (
            <Link
              key={course.id}
              href={`/dashboard/courses/${course.id}`}
              className="block rounded-lg border bg-card p-5 hover:shadow-sm transition-shadow"
            >
              <p className="font-medium">{course.name}</p>
              <p className="text-sm text-muted-foreground mt-1">{course.slug}</p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
