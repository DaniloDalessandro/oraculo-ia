"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";

interface ApiError {
  detail?: string;
}

function LoginForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const isWhatsAppFlow = Boolean(token);

  const handleStandardLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, senha }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError((data as ApiError).detail || "Erro ao fazer login.");
        return;
      }

      localStorage.setItem("access_token", data.access_token);
      setSuccess("Login realizado! Redirecionando...");
      setTimeout(() => {
        window.location.href = "/dashboard";
      }, 1500);
    } catch {
      setError("Erro de conexao. Verifique sua internet.");
    } finally {
      setLoading(false);
    }
  };

  const handleWhatsAppLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const res = await fetch("/api/auth/verify-token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, email, senha }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError((data as ApiError).detail || "Erro ao verificar token.");
        return;
      }

      localStorage.setItem("access_token", data.access_token);
      setSuccess(data.message || "WhatsApp vinculado com sucesso!");
    } catch {
      setError("Erro de conexao. Verifique sua internet.");
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="flex flex-col items-center justify-center text-center gap-4 py-8">
        <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center text-3xl">
          ✅
        </div>
        <h2 className="text-xl font-semibold text-white">{success}</h2>
        {isWhatsAppFlow && (
          <p className="text-gray-400 text-sm">
            Voce ja pode fechar esta aba e voltar ao WhatsApp.
          </p>
        )}
      </div>
    );
  }

  return (
    <form
      onSubmit={isWhatsAppFlow ? handleWhatsAppLogin : handleStandardLogin}
      className="w-full flex flex-col gap-5"
    >
      {/* Header */}
      <div className="text-center mb-2">
        <div className="w-12 h-12 bg-blue-600/20 rounded-xl flex items-center justify-center text-2xl mx-auto mb-4">
          🤖
        </div>
        <h1 className="text-2xl font-bold text-white">
          {isWhatsAppFlow ? "Vincular WhatsApp" : "Entrar na plataforma"}
        </h1>
        <p className="text-gray-400 text-sm mt-1">
          {isWhatsAppFlow
            ? "Faca login para ativar seu assistente"
            : "Acesse sua conta corporativa"}
        </p>
      </div>

      {/* Badge WhatsApp */}
      {isWhatsAppFlow && (
        <div className="flex items-start gap-3 bg-green-500/10 border border-green-500/20 rounded-xl px-4 py-3">
          <span className="text-green-400 text-lg mt-0.5">📱</span>
          <p className="text-green-300 text-xs leading-relaxed">
            Link de autenticacao do WhatsApp detectado. Faca login para vincular
            seu numero.
          </p>
        </div>
      )}

      {/* Erro */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {/* Email */}
      <div className="flex flex-col gap-1.5">
        <label className="text-sm text-gray-300 font-medium">E-mail</label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="seu@email.com"
          required
          disabled={loading}
          className="bg-[#1c1c1c] border border-[#2a2a2a] rounded-xl px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/50 transition disabled:opacity-50 text-sm"
        />
      </div>

      {/* Senha */}
      <div className="flex flex-col gap-1.5">
        <label className="text-sm text-gray-300 font-medium">Senha</label>
        <input
          type="password"
          value={senha}
          onChange={(e) => setSenha(e.target.value)}
          placeholder="••••••••"
          required
          disabled={loading}
          className="bg-[#1c1c1c] border border-[#2a2a2a] rounded-xl px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/50 transition disabled:opacity-50 text-sm"
        />
      </div>

      {/* Botao */}
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
        ) : isWhatsAppFlow ? (
          "Vincular WhatsApp"
        ) : (
          "Entrar"
        )}
      </button>

      {/* Esqueci senha */}
      {!isWhatsAppFlow && (
        <div className="text-center">
          <button
            type="button"
            className="text-xs text-gray-600 hover:text-gray-400 transition-colors"
            onClick={() => alert("Funcionalidade disponivel em breve.")}
          >
            Esqueci minha senha
          </button>
        </div>
      )}
    </form>
  );
}

export default function LoginPage() {
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
            <LoginForm />
          </Suspense>
        </div>

        <p className="text-center text-xs text-gray-700 mt-6">
          Oraculo IA &copy; {new Date().getFullYear()} &mdash; Plataforma corporativa
        </p>
      </div>
    </main>
  );
}
