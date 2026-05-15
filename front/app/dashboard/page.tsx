"use client"

import { useEffect, useState } from "react"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts"

interface DashboardStats {
  total_atracacoes: number
  atracacoes_ano: number
  ano: number
  plr_medio: number
  bercos_ativos: number
  tonelagem_total: number
  atracacoes_por_mes: { mes: string; total: number }[]
  top_bercos: { berco: string; total: number }[]
}

function fmtInt(n: number) {
  return n.toLocaleString("pt-BR")
}

function fmtTonelagem(n: number) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1).replace(".", ",")}M t`
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K t`
  return `${n} t`
}

export default function DashboardHome() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch("/api/stats")
      .then((r) => r.json())
      .then((d) => {
        if (!d.error) setStats(d)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const kpis = stats
    ? [
        {
          label: `Atracações (${stats.ano})`,
          value: fmtInt(stats.atracacoes_ano),
          sub: `${fmtInt(stats.total_atracacoes)} total registrado`,
        },
        {
          label: "Tonelagem DWT",
          value: fmtTonelagem(stats.tonelagem_total),
          sub: "Capacidade total registrada",
        },
        {
          label: "PLR médio",
          value: stats.plr_medio > 0 ? `${stats.plr_medio.toFixed(1).replace(".", ",")} t/h` : "—",
          sub: "Prancha de carregamento",
        },
        {
          label: "Berços",
          value: fmtInt(stats.bercos_ativos),
          sub: "Berços com operações",
        },
      ]
    : [
        { label: "Atracações (ano)", value: "—", sub: "Total registrado" },
        { label: "Tonelagem DWT", value: "—", sub: "Capacidade total" },
        { label: "PLR médio", value: "—", sub: "t/h" },
        { label: "Berços", value: "—", sub: "Com operações" },
      ]

  return (
    <div className="flex flex-col h-full min-h-svh">
      <header className="flex h-14 shrink-0 items-center gap-3 px-4 border-b border-white/8">
        <SidebarTrigger className="text-white/50 hover:text-white transition-colors" />
        <Separator
          orientation="vertical"
          className="h-4 bg-white/10 data-vertical:h-4 data-vertical:self-auto"
        />
        <span className="text-sm font-medium text-white/60">Dashboard</span>
      </header>

      <div className="flex-1 p-6 space-y-8">
        {/* Hero */}
        <div className="space-y-1">
          <h1 className="text-white" style={{ fontSize: "35px", fontWeight: 300 }}>
            Visão Geral
          </h1>
          <p className="text-white/40 text-sm">Porto de Itaguaí — dados operacionais</p>
        </div>

        {/* KPI cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {kpis.map((s) => (
            <div
              key={s.label}
              className="rounded-lg bg-[#121314] border border-white/8 p-6 space-y-3"
            >
              <p className="text-xs text-white/40 font-medium uppercase tracking-wider">
                {s.label}
              </p>
              {loading ? (
                <Skeleton className="h-9 w-24 bg-white/8" />
              ) : (
                <p className="text-3xl font-light text-white">{s.value}</p>
              )}
              <p className="text-xs text-white/25">{s.sub}</p>
            </div>
          ))}
        </div>

        {/* CTA band */}
        <div className="rounded-lg bg-[#0070d1] p-8 flex flex-col sm:flex-row sm:items-center justify-between gap-6">
          <div className="space-y-1">
            <h2 className="text-white font-semibold text-lg">Consulte com ITA</h2>
            <p className="text-white/70 text-sm">
              Faça perguntas em linguagem natural sobre atracações, cargas e operações.
            </p>
          </div>
          <a
            href="/dashboard/ita"
            className="shrink-0 inline-flex items-center gap-2 h-11 px-6 rounded-full bg-white text-[#0070d1] text-sm font-bold hover:bg-white/90 transition-colors"
          >
            Abrir ITA
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path
                d="M2 7h10M8 3l4 4-4 4"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </a>
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Atracações por mês */}
          <div className="lg:col-span-2 rounded-lg bg-[#121314] border border-white/8 p-6 flex flex-col gap-4">
            <p className="text-xs text-white/40 font-medium uppercase tracking-wider shrink-0">
              Atracações por mês (últimos 12 meses)
            </p>
            {loading ? (
              <Skeleton className="flex-1 min-h-52 bg-white/5 rounded" />
            ) : stats && stats.atracacoes_por_mes.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart
                  data={stats.atracacoes_por_mes}
                  margin={{ top: 4, right: 8, left: -20, bottom: 4 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                  <XAxis
                    dataKey="mes"
                    tick={{ fontSize: 11, fill: "rgba(255,255,255,0.3)" }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: "rgba(255,255,255,0.3)" }}
                    tickLine={false}
                    axisLine={false}
                    allowDecimals={false}
                  />
                  <Tooltip
                    contentStyle={{
                      fontSize: 12,
                      borderRadius: 8,
                      border: "1px solid rgba(255,255,255,0.1)",
                      background: "#1a1b1c",
                      color: "#fff",
                    }}
                    cursor={{ fill: "rgba(255,255,255,0.04)" }}
                  />
                  <Bar dataKey="total" fill="#0070d1" radius={[4, 4, 0, 0]} name="Atracações" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex-1 flex items-center justify-center min-h-52">
                <p className="text-white/20 text-sm">Sem dados no período</p>
              </div>
            )}
          </div>

          {/* Top berços */}
          <div className="rounded-lg bg-[#121314] border border-white/8 p-6 flex flex-col gap-4">
            <p className="text-xs text-white/40 font-medium uppercase tracking-wider shrink-0">
              Top berços
            </p>
            {loading ? (
              <div className="space-y-2 flex-1">
                {Array.from({ length: 6 }).map((_, i) => (
                  <Skeleton key={i} className="h-7 bg-white/5 rounded" />
                ))}
              </div>
            ) : stats && stats.top_bercos.length > 0 ? (
              <div className="flex-1 flex flex-col gap-2 justify-center">
                {stats.top_bercos.map((b, i) => {
                  const max = stats.top_bercos[0].total
                  const pct = Math.round((b.total / max) * 100)
                  return (
                    <div key={b.berco} className="flex items-center gap-3">
                      <span className="text-[11px] text-white/30 w-4 text-right shrink-0">
                        {i + 1}
                      </span>
                      <span className="text-xs text-white/60 w-10 shrink-0 truncate">
                        {b.berco}
                      </span>
                      <div className="flex-1 bg-white/5 rounded-full h-1.5 overflow-hidden">
                        <div
                          className="h-full bg-[#0070d1] rounded-full transition-all"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-[11px] text-white/40 w-10 text-right shrink-0 tabular-nums">
                        {fmtInt(b.total)}
                      </span>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center">
                <p className="text-white/20 text-sm">Sem dados</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
