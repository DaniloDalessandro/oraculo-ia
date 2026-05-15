import { NextRequest, NextResponse } from "next/server"
import { cookies } from "next/headers"

const API_URL = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001"

async function getToken() {
  const cookieStore = await cookies()
  return cookieStore.get("session_token")?.value
}

export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const token = await getToken()
  if (!token) return NextResponse.json({ error: "Não autenticado." }, { status: 401 })
  const { id } = await params
  try {
    const res = await fetch(`${API_URL}/ai-agent/atracacoes/${id}/`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    })
    return NextResponse.json(await res.json(), { status: res.status })
  } catch {
    return NextResponse.json({ error: "Erro ao conectar com o servidor." }, { status: 502 })
  }
}

export async function PATCH(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const token = await getToken()
  if (!token) return NextResponse.json({ error: "Não autenticado." }, { status: 401 })
  const { id } = await params
  try {
    const body = await request.json()
    const res = await fetch(`${API_URL}/ai-agent/atracacoes/${id}/`, {
      method: "PATCH",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
    return NextResponse.json(await res.json(), { status: res.status })
  } catch {
    return NextResponse.json({ error: "Erro ao conectar com o servidor." }, { status: 502 })
  }
}

export async function DELETE(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const token = await getToken()
  if (!token) return NextResponse.json({ error: "Não autenticado." }, { status: 401 })
  const { id } = await params
  try {
    const res = await fetch(`${API_URL}/ai-agent/atracacoes/${id}/`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    })
    if (res.status === 204) return new NextResponse(null, { status: 204 })
    return NextResponse.json(await res.json(), { status: res.status })
  } catch {
    return NextResponse.json({ error: "Erro ao conectar com o servidor." }, { status: 502 })
  }
}
