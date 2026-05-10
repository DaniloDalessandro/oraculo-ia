import { NextResponse } from "next/server"
import { cookies } from "next/headers"

const API_URL = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001"

export async function GET() {
  const cookieStore = await cookies()
  const token = cookieStore.get("session_token")?.value

  if (!token) {
    return NextResponse.json({ error: "Não autenticado." }, { status: 401 })
  }

  try {
    const upstream = await fetch(`${API_URL}/ai-agent/schema/detail/`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    })
    const data = await upstream.json()
    return NextResponse.json(data, { status: upstream.status })
  } catch {
    return NextResponse.json({ error: "Erro ao conectar com o servidor." }, { status: 502 })
  }
}
