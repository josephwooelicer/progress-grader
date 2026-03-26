import Link from "next/link";
import LogoutButton from "@/components/ui/LogoutButton";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b bg-card px-6 py-3 flex items-center justify-between">
        <Link href="/dashboard" className="font-semibold text-lg">
          Progress Grader
        </Link>
        <LogoutButton />
      </header>
      <main className="flex-1 p-6 max-w-6xl mx-auto w-full">{children}</main>
    </div>
  );
}
