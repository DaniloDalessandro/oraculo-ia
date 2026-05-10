"use server"

import { redirect } from "next/navigation"
import { createSession, deleteSession } from "@/app/lib/session"

const API_URL =
  process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export type LoginState =
  | { error: string }
  | { success: true }
  | undefined

export async function loginAction(
  _prevState: LoginState,
  formData: FormData
): Promise<LoginState> {
  const email = formData.get("email") as string
  const password = formData.get("password") as string

  if (!email || !password) {
    return { error: "Preencha todos os campos." }
  }

  let data: { access?: string; error?: string }

  try {
    const res = await fetch(`${API_URL}/api/auth/login/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    })

    data = await res.json()

    if (!res.ok) {
      return { error: data.error ?? "Credenciais inválidas." }
    }
  } catch {
    return { error: "Não foi possível conectar ao servidor." }
  }

  await createSession(data.access!)
  redirect("/dashboard")
}

export async function logoutAction() {
  await deleteSession()
  redirect("/login")
}
