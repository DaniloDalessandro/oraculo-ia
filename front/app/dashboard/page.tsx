import { SidebarTrigger } from "@/components/ui/sidebar"
import { Separator } from "@/components/ui/separator"

const stats = [
  { label: "Atracações (2025)", value: "—", sub: "Total registrado" },
  { label: "Tonelagem movimentada", value: "—", sub: "Carga total" },
  { label: "PLR médio", value: "—", sub: "t/h" },
  { label: "Berços ativos", value: "—", sub: "Em operação" },
]

export default function DashboardHome() {
  return (
    <div className="flex flex-col h-full min-h-svh">
      {/* Top bar */}
      <header className="flex h-14 shrink-0 items-center gap-3 px-4 border-b border-white/8">
        <SidebarTrigger className="text-white/50 hover:text-white transition-colors" />
        <Separator orientation="vertical" className="h-4 bg-white/10 data-vertical:h-4 data-vertical:self-auto" />
        <span className="text-sm font-medium text-white/60">Dashboard</span>
      </header>

      <div className="flex-1 p-6 space-y-8">
        {/* Hero */}
        <div className="space-y-1">
          <h1
            className="text-white"
            style={{ fontSize: "35px", fontWeight: 300, letterSpacing: 0 }}
          >
            Visão Geral
          </h1>
          <p className="text-white/40 text-sm">Porto de Itaguaí — dados operacionais</p>
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {stats.map((s) => (
            <div
              key={s.label}
              className="rounded-lg bg-[#121314] border border-white/8 p-6 space-y-3"
            >
              <p className="text-xs text-white/40 font-medium uppercase tracking-wider">{s.label}</p>
              <p className="text-3xl font-light text-white" style={{ fontWeight: 300 }}>{s.value}</p>
              <p className="text-xs text-white/25">{s.sub}</p>
            </div>
          ))}
        </div>

        {/* Quick access band */}
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
            style={{ borderRadius: "9999px" }}
          >
            Abrir ITA
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M2 7h10M8 3l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </a>
        </div>

        {/* Placeholder charts */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 rounded-lg bg-[#121314] border border-white/8 p-6 min-h-64 flex flex-col gap-3">
            <p className="text-xs text-white/40 font-medium uppercase tracking-wider">Atracações por mês</p>
            <div className="flex-1 flex items-center justify-center">
              <p className="text-white/20 text-sm">Consulte via ITA para gerar gráficos</p>
            </div>
          </div>
          <div className="rounded-lg bg-[#121314] border border-white/8 p-6 min-h-64 flex flex-col gap-3">
            <p className="text-xs text-white/40 font-medium uppercase tracking-wider">Top berços</p>
            <div className="flex-1 flex items-center justify-center">
              <p className="text-white/20 text-sm">Em breve</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
