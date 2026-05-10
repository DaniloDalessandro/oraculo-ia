import { NextRequest, NextResponse } from "next/server"
import { cookies } from "next/headers"

const API_URL = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001"

async function handler(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const cookieStore = await cookies()
  const token = cookieStore.get("session_token")?.value
  if (!token) return NextResponse.json({ error: "Não autenticado." }, { status: 401 })

  const { id } = await params
  const upstream = await fetch(`${API_URL}/ai-agent/glossary/${id}/`, {
    method: request.method,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: request.method !== "GET" && request.method !== "DELETE" ? await request.text() : undefined,
  })
  if (upstream.status === 204) return new NextResponse(null, { status: 204 })
  const data = await upstream.json()
  return NextResponse.json(data, { status: upstream.status })
}

export { handler as GET, handler as PUT, handler as PATCH, handler as DELETE }
