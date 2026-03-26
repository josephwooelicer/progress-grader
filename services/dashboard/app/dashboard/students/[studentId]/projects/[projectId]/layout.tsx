import Link from "next/link";

interface Props {
  children: React.ReactNode;
  params: { studentId: string; projectId: string };
}

export default function StudentProjectLayout({ children, params }: Props) {
  const { studentId, projectId } = params;
  const base = `/dashboard/students/${studentId}/projects/${projectId}`;

  return (
    <div>
      <nav className="flex gap-1 mb-6 border-b">
        {(["timeline", "rubric", "git"] as const).map((tab) => (
          <Link
            key={tab}
            href={`${base}/${tab}`}
            className="px-4 py-2 text-sm font-medium capitalize text-muted-foreground hover:text-foreground border-b-2 border-transparent hover:border-primary -mb-px transition-colors"
          >
            {tab === "git" ? "Git" : tab.charAt(0).toUpperCase() + tab.slice(1)}
          </Link>
        ))}
        <div className="flex-1" />
        <a
          href={`/api/backend/api/teacher/projects/${projectId}/rubric/export.csv`}
          className="px-4 py-2 text-sm text-muted-foreground hover:text-foreground -mb-px"
          download
        >
          Export CSV
        </a>
      </nav>
      {children}
    </div>
  );
}
