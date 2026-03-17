"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Nav from "@/components/Nav";
import { apiFetch, getToken, type DashboardStats } from "@/lib/api";

function StatCard({
  label,
  value,
  icon,
  sub,
}: {
  label: string;
  value: string | number;
  icon: string;
  sub?: string;
}) {
  return (
    <div className="bg-[#141414] border border-[#222] rounded-xl p-5">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-gray-500 text-xs font-medium uppercase tracking-wide">
            {label}
          </p>
          <p className="text-3xl font-bold text-white mt-1">{value}</p>
          {sub && <p className="text-gray-600 text-xs mt-1">{sub}</p>}
        </div>
        <span className="text-2xl">{icon}</span>
      </div>
    </div>
  );
}

function formatPhone(phone: string) {
  if (phone.length === 13)
    return `+${phone.slice(0, 2)} (${phone.slice(2, 4)}) ${phone.slice(4, 9)}-${phone.slice(9)}`;
  return phone;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const REFRESH_INTERVAL = 30_000; // 30 segundos

export default function DashboardPage() {
  const router = useRouter();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchStats = useCallback(async () => {
    try {
      const data = await apiFetch<DashboardStats>("/dashboard/stats");
      setStats(data);
      setLastUpdated(new Date());
      setError("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Erro ao carregar dados");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    fetchStats();
    intervalRef.current = setInterval(fetchStats, REFRESH_INTERVAL);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [router, fetchStats]);

  return (
    <div className="min-h-screen bg-[#0f0f0f]">
      <Nav />
      <main className="pt-14 px-6 max-w-5xl mx-auto py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-gray-500 text-sm mt-1">
            Visão geral do sistema em tempo real
          </p>
        </div>

        {loading && (
          <div className="flex justify-center py-20">
            <span className="w-8 h-8 border-2 border-[#333] border-t-blue-500 rounded-full animate-spin" />
          </div>
        )}

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-red-400 text-sm">
            {error}
          </div>
        )}

        {stats && (
          <>
            {/* Stats grid — linha 1 */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
              <StatCard
                label="Total de mensagens"
                value={stats.total_mensagens}
                icon="💬"
              />
              <StatCard
                label="Usuários ativos"
                value={stats.usuarios_ativos}
                icon="👥"
              />
              <StatCard
                label="Mensagens hoje"
                value={stats.mensagens_hoje}
                icon="📅"
              />
              <StatCard
                label="WhatsApp"
                value={stats.whatsapp_conectado ? "Conectado" : "Offline"}
                icon={stats.whatsapp_conectado ? "🟢" : "🔴"}
                sub={
                  stats.whatsapp_conectado
                    ? "Evolution API ativa"
                    : "Verifique a conexão"
                }
              />
            </div>

            {/* Stats grid — linha 2 (Sprint 4) */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              <StatCard
                label="IA hoje"
                value={stats.total_ia_hoje}
                icon="🧠"
                sub="consultas processadas"
              />
              <StatCard
                label="Tempo médio IA"
                value={`${stats.tempo_medio_resposta_ms.toFixed(0)} ms`}
                icon="⚡"
                sub="por consulta"
              />
              <StatCard
                label="Taxa de erro IA"
                value={`${stats.taxa_erro_ia_pct}%`}
                icon={stats.taxa_erro_ia_pct > 10 ? "🔴" : "✅"}
                sub="consultas com falha"
              />
              <StatCard
                label="Cache hit rate"
                value={`${stats.cache_hit_rate}%`}
                icon="💾"
                sub={`${stats.workers_ativos} worker(s) ativo(s)`}
              />
            </div>

            {/* Recent messages */}
            <div className="bg-[#141414] border border-[#222] rounded-xl overflow-hidden">
              <div className="px-6 py-4 border-b border-[#222]">
                <h2 className="text-sm font-semibold text-white">
                  Últimas mensagens
                </h2>
              </div>

              {stats.ultimas_mensagens.length === 0 ? (
                <div className="px-6 py-10 text-center text-gray-600 text-sm">
                  Nenhuma mensagem ainda. Conecte o WhatsApp para começar.
                </div>
              ) : (
                <div className="divide-y divide-[#1e1e1e]">
                  {stats.ultimas_mensagens.map((m, i) => (
                    <div key={i} className="px-6 py-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-mono text-blue-400">
                          {formatPhone(m.telefone)}
                        </span>
                        <span className="text-xs text-gray-600">
                          {formatDate(m.created_at)}
                        </span>
                      </div>
                      <p className="text-sm text-gray-300 truncate">
                        <span className="text-gray-600 mr-1">→</span>
                        {m.mensagem_usuario}
                      </p>
                      <p className="text-xs text-gray-600 truncate mt-1">
                        <span className="text-gray-700 mr-1">←</span>
                        {m.resposta_sistema}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
