import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://backend:8000";
const IS_PROD = process.env.NODE_ENV === "production";

export async function POST(request: NextRequest) {
  const body = await request.text();
  const upstream = await fetch(`${BACKEND_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });

  const data = await upstream.json();
  const response = NextResponse.json(data, { status: upstream.status });

  if (upstream.ok) {
    // getSetCookie() returns each Set-Cookie header as a separate string,
    // unlike forEach which collapses them into one (Node.js fetch quirk).
    const cookies = (upstream.headers as any).getSetCookie?.() ??
      upstream.headers.get("set-cookie")?.split(/,(?=[^;])/) ?? [];

    for (const cookie of cookies) {
      // Strip Secure flag in non-production so cookies work over plain HTTP in dev
      const value = IS_PROD ? cookie : cookie.replace(/;\s*secure/gi, "");
      response.headers.append("Set-Cookie", value);
    }
  }

  return response;
}
