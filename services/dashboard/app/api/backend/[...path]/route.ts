import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://backend:8000";

async function proxy(request: NextRequest, path: string[]): Promise<NextResponse> {
  const upstreamPath = "/" + path.join("/");
  const search = request.nextUrl.search;
  const url = `${BACKEND_URL}${upstreamPath}${search}`;

  const cookieHeader = request.headers.get("cookie") ?? "";
  const contentType = request.headers.get("content-type") ?? "";

  const headers: Record<string, string> = {
    cookie: cookieHeader,
  };
  if (contentType) headers["content-type"] = contentType;

  const body = request.method !== "GET" && request.method !== "HEAD"
    ? await request.arrayBuffer()
    : undefined;

  const upstream = await fetch(url, {
    method: request.method,
    headers,
    body: body ? Buffer.from(body) : undefined,
  });

  // Stream CSV and other binary responses directly
  const upstreamContentType = upstream.headers.get("content-type") ?? "";
  if (upstreamContentType.includes("text/csv") || upstreamContentType.includes("application/octet-stream")) {
    const blob = await upstream.blob();
    const response = new NextResponse(blob, { status: upstream.status });
    upstream.headers.forEach((value, key) => {
      if (key.toLowerCase() !== "transfer-encoding") {
        response.headers.set(key, value);
      }
    });
    return response;
  }

  const data = await upstream.text();
  const response = new NextResponse(data, {
    status: upstream.status,
    headers: { "content-type": upstreamContentType || "application/json" },
  });
  return response;
}

export async function GET(request: NextRequest, { params }: { params: { path: string[] } }) {
  return proxy(request, params.path);
}
export async function POST(request: NextRequest, { params }: { params: { path: string[] } }) {
  return proxy(request, params.path);
}
export async function PUT(request: NextRequest, { params }: { params: { path: string[] } }) {
  return proxy(request, params.path);
}
export async function DELETE(request: NextRequest, { params }: { params: { path: string[] } }) {
  return proxy(request, params.path);
}
