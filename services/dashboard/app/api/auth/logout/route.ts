import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://backend:8000";

export async function POST(request: NextRequest) {
  const cookieHeader = request.headers.get("cookie") ?? "";
  await fetch(`${BACKEND_URL}/auth/logout`, {
    method: "POST",
    headers: { cookie: cookieHeader },
  });

  const response = NextResponse.json({ ok: true });
  response.cookies.delete("access_token");
  response.cookies.delete("refresh_token");
  return response;
}
