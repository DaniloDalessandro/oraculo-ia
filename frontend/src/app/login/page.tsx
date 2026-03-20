"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";

interface ApiError {
  detail?: string;
}

type View = "login" | "forgot" | "forgot-sent";

function LoginForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [view, setView] = useState<View>("login");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [forgotEmail, setForgotEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [countdown, setCountdown] = useState(0);

  const isWhatsAppFlow = Boolean(token);

  const startCloseCountdown = useCallback(() => {
    setCountdown(3);
  }, []);

  useEffect(() => {
    if (countdown <= 0) return;
    if (countdown === 1) {
      const t = setTimeout(() => window.close(), 1000);
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => setCountdown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [countdown]);

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
      setSuccess(data.message || "Login realizado com sucesso!");
      startCloseCountdown();
    } catch {
      setError("Erro de conexao. Verifique sua internet.");
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const res = await fetch("/api/auth/forgot-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: forgotEmail }),
      });

      if (!res.ok) {
        const data = await res.json();
        setError((data as ApiError).detail || "Erro ao processar solicitacao.");
        return;
      }

      setView("forgot-sent");
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
          <>
            <p className="text-gray-400 text-sm">
              Volte ao WhatsApp — o assistente ja enviou uma mensagem para voce.
            </p>
            {countdown > 0 && (
              <p className="text-gray-600 text-xs">
                Esta aba sera fechada em {countdown}s...
              </p>
            )}
            <button
              type="button"
              onClick={() => window.close()}
              className="mt-2 text-xs bg-green-600 hover:bg-green-500 text-white px-4 py-2 rounded-lg transition-colors"
            >
              Fechar aba
            </button>
          </>
        )}
      </div>
    );
  }

  /* ── Tela: link enviado ── */
  if (view === "forgot-sent") {
    return (
      <div className="flex flex-col items-center justify-center text-center gap-4 py-6">
        <div className="w-16 h-16 bg-blue-500/20 rounded-full flex items-center justify-center text-3xl">
          📧
        </div>
        <h2 className="text-xl font-semibold text-white">Verifique seu e-mail</h2>
        <p className="text-gray-400 text-sm leading-relaxed">
          Se o endereço <span className="text-white font-medium">{forgotEmail}</span> estiver
          cadastrado, voce recebera um link para redefinir sua senha em breve.
        </p>
        <p className="text-gray-600 text-xs">O link expira em 30 minutos.</p>
        <button
          type="button"
          onClick={() => {
            setView("login");
            setError("");
            setForgotEmail("");
          }}
          className="mt-2 text-sm text-blue-400 hover:text-blue-300 transition-colors"
        >
          Voltar ao login
        </button>
      </div>
    );
  }

  /* ── Tela: solicitar recuperacao ── */
  if (view === "forgot") {
    return (
      <form onSubmit={handleForgotPassword} className="w-full flex flex-col gap-5">
        <div className="text-center mb-2">
          <div className="w-12 h-12 bg-yellow-600/20 rounded-xl flex items-center justify-center text-2xl mx-auto mb-4">
            🔑
          </div>
          <h1 className="text-2xl font-bold text-white">Recuperar senha</h1>
          <p className="text-gray-400 text-sm mt-1">
            Informe seu e-mail para receber o link de redefinicao
          </p>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3">
            <p className="text-red-400 text-sm">{error}</p>
          </div>
        )}

        <div className="flex flex-col gap-1.5">
          <label className="text-sm text-gray-300 font-medium">E-mail</label>
          <input
            type="email"
            value={forgotEmail}
            onChange={(e) => setForgotEmail(e.target.value)}
            placeholder="seu@email.com"
            required
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
            "Enviar link de recuperacao"
          )}
        </button>

        <div className="text-center">
          <button
            type="button"
            onClick={() => {
              setView("login");
              setError("");
            }}
            className="text-xs text-gray-600 hover:text-gray-400 transition-colors"
          >
            Voltar ao login
          </button>
        </div>
      </form>
    );
  }

  /* ── Tela: login normal ── */
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
        <h1 className="text-2xl font-bold text-white">Entrar na plataforma</h1>
        <p className="text-gray-400 text-sm mt-1">Acesse sua conta corporativa</p>
      </div>

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
        ) : (
          "Entrar"
        )}
      </button>

      {/* Recuperar senha */}
      {!isWhatsAppFlow && (
        <div className="text-center">
          <button
            type="button"
            onClick={() => {
              setView("forgot");
              setError("");
            }}
            className="text-xs text-gray-600 hover:text-gray-400 transition-colors"
          >
            Recuperar senha
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
