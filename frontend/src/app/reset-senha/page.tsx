"use client";

import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";

interface ApiError {
  detail?: string;
}

function ResetSenhaForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [novaSenha, setNovaSenha] = useState("");
  const [confirmarSenha, setConfirmarSenha] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (novaSenha.length < 6) {
      setError("A senha deve ter pelo menos 6 caracteres.");
      return;
    }
    if (novaSenha !== confirmarSenha) {
      setError("As senhas nao coincidem.");
      return;
    }

    setLoading(true);

    try {
      const res = await fetch("/api/auth/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, nova_senha: novaSenha }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError((data as ApiError).detail || "Erro ao redefinir senha.");
        return;
      }

      setSuccess(true);
      setTimeout(() => {
        window.location.href = "/login";
      }, 3000);
    } catch {
      setError("Erro de conexao. Verifique sua internet.");
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="flex flex-col items-center text-center gap-4 py-6">
        <div className="text-4xl">⚠️</div>
        <h2 className="text-xl font-semibold text-white">Link invalido</h2>
        <p className="text-gray-400 text-sm">
          Este link de recuperacao e invalido ou ja foi utilizado.
        </p>
        <a
          href="/login"
          className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
        >
          Voltar ao login
        </a>
      </div>
    );
  }

  if (success) {
    return (
      <div className="flex flex-col items-center text-center gap-4 py-6">
        <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center text-3xl">
          ✅
        </div>
        <h2 className="text-xl font-semibold text-white">Senha redefinida!</h2>
        <p className="text-gray-400 text-sm">
          Sua senha foi alterada com sucesso. Redirecionando para o login...
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="w-full flex flex-col gap-5">
      <div className="text-center mb-2">
        <div className="w-12 h-12 bg-blue-600/20 rounded-xl flex items-center justify-center text-2xl mx-auto mb-4">
          🔒
        </div>
        <h1 className="text-2xl font-bold text-white">Nova senha</h1>
        <p className="text-gray-400 text-sm mt-1">Digite e confirme sua nova senha</p>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      <div className="flex flex-col gap-1.5">
        <label className="text-sm text-gray-300 font-medium">Nova senha</label>
        <input
          type="password"
          value={novaSenha}
          onChange={(e) => setNovaSenha(e.target.value)}
          placeholder="••••••••"
          required
          minLength={6}
          disabled={loading}
          className="bg-[#1c1c1c] border border-[#2a2a2a] rounded-xl px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/50 transition disabled:opacity-50 text-sm"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-sm text-gray-300 font-medium">Confirmar senha</label>
        <input
          type="password"
          value={confirmarSenha}
          onChange={(e) => setConfirmarSenha(e.target.value)}
          placeholder="••••••••"
          required
          minLength={6}
          disabled={loading}
          className="bg-[#1c1c1c] border border-[#2a2a2a] rounded-xl px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/50 transition disabled:opacity-50 text-sm"
        />
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-blue-600 hover:bg-blue-500 active:bg-blue-700 disabled:bg-blue-800 disabled:cursor-not-allowed text-white font-semibold py-3 px-4 rounded-xl transition-colors flex items-center justify-center gap-2 text-sm"
      >
        {loading ? (
          <>
            <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            Aguarde...
          </>
        ) : (
          "Redefinir senha"
        )}
      </button>

      <div className="text-center">
        <a
          href="/login"
          className="text-xs text-gray-600 hover:text-gray-400 transition-colors"
        >
          Voltar ao login
        </a>
      </div>
    </form>
  );
}

export default function ResetSenhaPage() {
  return (
    <main className="min-h-screen flex items-center justify-center p-4 bg-[#0f0f0f]">
      <div className="w-full max-w-sm">
        <div className="bg-[#141414] border border-[#1e1e1e] rounded-2xl p-8 shadow-2xl">
          <Suspense
            fallback={
              <div className="flex items-center justify-center py-12">
                <span className="inline-block w-6 h-6 border-2 border-[#2a2a2a] border-t-blue-500 rounded-full animate-spin" />
              </div>
            }
          >
            <ResetSenhaForm />
          </Suspense>
        </div>

        <p className="text-center text-xs text-gray-700 mt-6">
          Oraculo IA &copy; {new Date().getFullYear()} &mdash; Plataforma corporativa
        </p>
      </div>
    </main>
  );
}
