import Link from "next/link";
import { cookies } from "next/headers";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://backend:8000";

interface StudentRow {
  id: string;
  name: string;
  email: string;
  consented: boolean;
  project_id: string;
  project_name: string;
}

async function fetchStudents(courseId: string, cookieHeader: string): Promise<StudentRow[]> {
  try {
    const res = await fetch(
      `${BACKEND_URL}/api/teacher/courses/${courseId}/students`,
      { headers: { cookie: cookieHeader }, cache: "no-store" }
    );
    if (!res.ok) return [];
    const data = await res.json();
    return data.students ?? [];
  } catch {
    return [];
  }
}

export default async function CoursePage({ params }: { params: { courseId: string } }) {
  const cookieStore = cookies();
  const cookieHeader = cookieStore.getAll().map((c) => `${c.name}=${c.value}`).join("; ");
  const students = await fetchStudents(params.courseId, cookieHeader);

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-6">Students</h1>
      {students.length === 0 ? (
        <p className="text-muted-foreground">No students found for this course.</p>
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
                    <span
                      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                        s.consented
                          ? "bg-green-100 text-green-800"
                          : "bg-yellow-100 text-yellow-800"
                      }`}
                    >
                      {s.consented ? "Consented" : "No consent"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {s.consented ? (
                      <div className="flex gap-3">
                        <Link
                          href={`/dashboard/students/${s.id}/projects/${s.project_id}/timeline`}
                          className="text-primary hover:underline"
                        >
                          Timeline
                        </Link>
                        <Link
                          href={`/dashboard/students/${s.id}/projects/${s.project_id}/rubric`}
                          className="text-primary hover:underline"
                        >
                          Rubric
                        </Link>
                        <Link
                          href={`/dashboard/students/${s.id}/projects/${s.project_id}/git`}
                          className="text-primary hover:underline"
                        >
                          Git
                        </Link>
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
