"use client"

import { useActionState } from "react"
import { loginAction } from "@/app/actions/auth"

export function LoginForm() {
  const [state, action, pending] = useActionState(loginAction, undefined)

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="space-y-1">
        <h2 className="text-white text-2xl font-semibold">Entrar</h2>
        <p className="text-white/40 text-sm">Acesse sua conta para continuar</p>
      </div>

      <form action={action} className="space-y-4">
        {state && "error" in state && (
          <div className="rounded-lg bg-[#c81b3a]/10 border border-[#c81b3a]/20 px-4 py-3 text-sm text-[#c81b3a]">
            {state.error}
          </div>
        )}

        {/* Email */}
        <div className="space-y-1.5">
          <label htmlFor="email" className="text-sm text-white/70 font-medium">
            Email
          </label>
          <input
            id="email"
            name="email"
            type="email"
            placeholder="seu@email.com"
            required
            className="w-full h-12 rounded-sm bg-white/8 border border-white/10 px-4 text-white placeholder:text-white/25 text-sm focus:outline-none focus:border-[#0070d1] focus:bg-white/10 transition-colors"
            style={{ borderRadius: "4px" }}
          />
        </div>

        {/* Password */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label htmlFor="password" className="text-sm text-white/70 font-medium">
              Senha
            </label>
            <a href="#" className="text-xs text-[#53b1ff] hover:text-[#0070d1] transition-colors">
              Esqueceu a senha?
            </a>
          </div>
          <input
            id="password"
            name="password"
            type="password"
            required
            className="w-full h-12 rounded-sm bg-white/8 border border-white/10 px-4 text-white placeholder:text-white/25 text-sm focus:outline-none focus:border-[#0070d1] focus:bg-white/10 transition-colors"
            style={{ borderRadius: "4px" }}
          />
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={pending}
          className="w-full h-12 rounded-full bg-[#0070d1] hover:bg-[#0064b7] active:bg-[#004d8d] text-white text-sm font-bold tracking-wide transition-colors disabled:opacity-50 disabled:cursor-not-allowed mt-2"
          style={{ borderRadius: "9999px" }}
        >
          {pending ? "Entrando..." : "Entrar"}
        </button>
      </form>

      {/* Footer */}
      <p className="text-center text-xs text-white/25">
        Ao entrar, você concorda com os{" "}
        <a href="#" className="text-white/40 hover:text-white/60 underline underline-offset-2 transition-colors">
          Termos de Uso
        </a>
      </p>
    </div>
  )
}
