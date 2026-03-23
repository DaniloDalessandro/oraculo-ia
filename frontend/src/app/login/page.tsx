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
      const t = setTimeout(() => {
        window.location.href = "whatsapp://";
      }, 1000);
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
        const detail = (data as ApiError).detail || "Erro ao verificar token.";
        if (res.status === 400 && detail.toLowerCase().includes("invalido")) {
          setError("Link expirado ou já utilizado. Envie qualquer mensagem no WhatsApp para receber um novo link de acesso.");
        } else {
          setError(detail);
        }
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
        <h2 className="text-xl font-semibold text-white">Login realizado com sucesso!</h2>
        {isWhatsAppFlow && (
          <>
            <p className="text-gray-400 text-sm">
              Voltando ao WhatsApp em {countdown > 0 ? `${countdown}s` : "instantes"}...
            </p>
            <a
              href="whatsapp://"
              className="mt-2 w-full bg-green-600 hover:bg-green-500 text-white font-semibold px-4 py-3 rounded-xl transition-colors flex items-center justify-center gap-2"
            >
              💬 Voltar ao WhatsApp
            </a>
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
            className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-xl px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500/30 transition disabled:opacity-50 text-sm"
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
        <div className="flex items-center justify-center gap-2 mb-3">
          <div className="w-10 h-10 bg-orange-500 rounded-xl flex items-center justify-center">
            <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/>
              <path d="m3.3 7 8.7 5 8.7-5"/>
              <path d="M12 22V12"/>
            </svg>
          </div>
          <span className="text-white font-bold text-xl tracking-tight">CBS</span>
        </div>
        <h1 className="text-2xl font-bold text-white">
          {isWhatsAppFlow ? "Confirmar identidade" : "Gestão de Estoque"}
        </h1>
        <p className="text-gray-400 text-sm mt-1">
          {isWhatsAppFlow
            ? "Digite suas credenciais de acesso ao sistema"
            : "Acesse sua conta para continuar"}
        </p>
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
          className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-xl px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500/30 transition disabled:opacity-50 text-sm"
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
          className="bg-[#1a1a1a] border border-[#2a2a2a] rounded-xl px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500/30 transition disabled:opacity-50 text-sm"
        />
      </div>

      {/* Botao */}
      <button
        type="submit"
        disabled={loading}
        className="w-full bg-orange-600 hover:bg-orange-500 active:bg-orange-700 disabled:bg-orange-900 disabled:cursor-not-allowed text-white font-semibold py-3 px-4 rounded-xl transition-colors flex items-center justify-center gap-2 text-sm"
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
    <main className="min-h-screen flex items-center justify-center p-4 bg-[#0a0a0a]">
      {/* Fundo com gradiente sutil */}
      <div className="absolute inset-0 bg-gradient-to-br from-orange-950/20 via-transparent to-transparent pointer-events-none" />

      <div className="w-full max-w-sm relative">
        {/* Card */}
        <div className="bg-[#111111] border border-orange-900/30 rounded-2xl p-8 shadow-2xl shadow-orange-950/20">
          <Suspense
            fallback={
              <div className="flex items-center justify-center py-12">
                <span className="inline-block w-6 h-6 border-2 border-orange-900/40 border-t-orange-500 rounded-full animate-spin" />
              </div>
            }
          >
            <LoginForm />
          </Suspense>
        </div>

        <p className="text-center text-xs text-gray-700 mt-6">
          CBS Gestão de Estoque &copy; {new Date().getFullYear()}
        </p>
      </div>
    </main>
  );
}
