import { NextRequest, NextResponse } from "next/server"
import { cookies } from "next/headers"

const API_URL = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001"

async function handler(request: NextRequest) {
  const cookieStore = await cookies()
  const token = cookieStore.get("session_token")?.value
  if (!token) return NextResponse.json({ error: "Não autenticado." }, { status: 401 })

  const url = new URL(request.url)
  const upstream = await fetch(`${API_URL}/ai-agent/rules/${url.search}`, {
    method: request.method,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: request.method !== "GET" ? await request.text() : undefined,
  })
  const data = await upstream.json()
  return NextResponse.json(data, { status: upstream.status })
}

export { handler as GET, handler as POST }
