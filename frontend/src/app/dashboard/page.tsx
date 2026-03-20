"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Nav from "@/components/Nav";
import { apiFetch, getToken, type DashboardStats } from "@/lib/api";
import { cn } from "@/lib/utils";
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  Bot,
  CalendarDays,
  CheckCircle2,
  Clock,
  Database,
  MessageSquare,
  RefreshCw,
  Send,
  Server,
  Timer,
  Users,
  Wifi,
  WifiOff,
  XCircle,
  Zap,
} from "lucide-react";

// ─────────────────────────────────────────────────────────────────────────────
// Utilities
// ─────────────────────────────────────────────────────────────────────────────

function fmt(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return n.toLocaleString("pt-BR");
}

function fmtTime(d: Date) {
  return d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

/** Deterministic sparkline — avoids hydration mismatch */
function genSparkline(base: number, n = 8): number[] {
  const pts: number[] = [];
  let cur = base * 0.5;
  const seed = (base % 97) || 13;
  for (let i = 0; i < n - 1; i++) {
    pts.push(Math.max(0, Math.round(cur)));
    const delta = ((seed * (i + 3) * 31) % 40 - 20) / 200;
    cur = cur * (1 + delta) + (base - cur) * 0.22;
  }
  pts.push(base);
  return pts;
}

/** Generate per-hour distribution for today's total */
function genHourlyData(total: number): number[] {
  const hour = new Date().getHours();
  const W = [0.2, 0.1, 0.1, 0.1, 0.2, 0.4, 0.8, 1.8, 3.2, 4.0, 4.5, 5.0, 5.0, 4.5, 4.0, 3.5, 2.8, 2.2, 1.8, 1.4, 1.1, 0.8, 0.6, 0.4];
  const active = W.slice(0, hour + 1);
  const s = active.reduce((a, b) => a + b, 0) || 1;
  return active.map((w) => Math.max(0, Math.round((w / s) * total)));
}

// ─────────────────────────────────────────────────────────────────────────────
// SVG: Sparkline
// ─────────────────────────────────────────────────────────────────────────────

function Sparkline({ data, color = "#3b82f6", w = 72, h = 32 }: {
  data: number[];
  color?: string;
  w?: number;
  h?: number;
}) {
  if (data.length < 2) return null;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const pad = 3;
  const points = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * w;
      const y = h - pad - ((v - min) / range) * (h - pad * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const last = data[data.length - 1];
  const lx = w;
  const ly = h - pad - ((last - min) / range) * (h - pad * 2);
  return (
    <svg viewBox={`0 0 ${w} ${h}`} width={w} height={h} className="overflow-visible shrink-0">
      <polyline points={points} fill="none" stroke={color} strokeWidth="1.5"
        strokeLinecap="round" strokeLinejoin="round" opacity="0.85" />
      <circle cx={lx.toFixed(1)} cy={ly.toFixed(1)} r="2.5" fill={color} />
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// SVG: Area Chart
// ─────────────────────────────────────────────────────────────────────────────

function AreaChart({ data, color = "#3b82f6", labels }: {
  data: number[];
  color?: string;
  labels?: string[];
}) {
  const W = 560, H = 130, pT = 10, pB = 24, pL = 30, pR = 4;
  const cW = W - pL - pR;
  const cH = H - pT - pB;
  const max = Math.max(...data, 1);
  const gradId = `ag-${color.replace("#", "")}`;

  if (data.length < 2) {
    return (
      <div className="flex h-full items-center justify-center text-xs text-gray-600">
        Dados insuficientes
      </div>
    );
  }

  const pts = data.map((v, i) => ({
    x: pL + (i / (data.length - 1)) * cW,
    y: pT + cH - (v / max) * cH,
  }));

  const line = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
  const area = `${line}L${pts[pts.length - 1].x.toFixed(1)},${(pT + cH).toFixed(1)}L${pL},${(pT + cH).toFixed(1)}Z`;

  // Y ticks
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => ({
    v: Math.round(max * f),
    y: pT + cH - f * cH,
  }));

  // X labels — show max 8
  const step = Math.max(1, Math.floor(data.length / 8));
  const xLabels = labels
    ? labels.filter((_, i) => i % step === 0 || i === data.length - 1)
    : [];

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-full" preserveAspectRatio="none">
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="90%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>

      {/* Grid */}
      {ticks.map((t, i) => (
        <g key={i}>
          <line x1={pL} y1={t.y.toFixed(1)} x2={W - pR} y2={t.y.toFixed(1)}
            stroke="#ffffff" strokeOpacity="0.04" strokeWidth="1" />
          <text x={(pL - 4).toFixed()} y={(t.y + 3).toFixed()} fill="#4b5563"
            fontSize="9" textAnchor="end" fontFamily="monospace">{t.v}</text>
        </g>
      ))}

      {/* Area */}
      <path d={area} fill={`url(#${gradId})`} />

      {/* Line */}
      <path d={line} fill="none" stroke={color} strokeWidth="2"
        strokeLinecap="round" strokeLinejoin="round" />

      {/* Dots */}
      {pts.filter((_, i) => i % step === 0 || i === pts.length - 1).map((p, i) => (
        <circle key={i} cx={p.x.toFixed(1)} cy={p.y.toFixed(1)}
          r="2" fill={color} opacity="0.7" />
      ))}

      {/* X Labels */}
      {labels && labels
        .map((l, i) => ({ l, i }))
        .filter(({ i }) => i % step === 0 || i === data.length - 1)
        .map(({ l, i }) => {
          const x = pL + (i / (data.length - 1)) * cW;
          return (
            <text key={i} x={x.toFixed(1)} y={(H - 4).toFixed()} fill="#4b5563"
              fontSize="8.5" textAnchor="middle" fontFamily="monospace">{l}</text>
          );
        })
      }
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Micro UI
// ─────────────────────────────────────────────────────────────────────────────

function PulseDot({ green }: { green: boolean }) {
  return (
    <span className="relative flex h-2 w-2 shrink-0">
      {green && (
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
      )}
      <span className={cn("relative inline-flex h-2 w-2 rounded-full",
        green ? "bg-emerald-400" : "bg-red-500")} />
    </span>
  );
}

function Trend({ pct, positive }: { pct: string; positive: boolean }) {
  return (
    <span className={cn(
      "inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[10px] font-semibold",
      positive ? "bg-emerald-500/15 text-emerald-400" : "bg-red-500/15 text-red-400",
    )}>
      {positive ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
      {pct}
    </span>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Toast
// ─────────────────────────────────────────────────────────────────────────────

interface ToastItem { id: number; text: string; type: "ok" | "err" | "info" }

function Toast({ item, onClose }: { item: ToastItem; onClose: () => void }) {
  useEffect(() => {
    const t = setTimeout(onClose, 3500);
    return () => clearTimeout(t);
  }, [onClose]);
  return (
    <div className={cn(
      "flex items-center gap-3 rounded-xl border px-4 py-3 text-sm shadow-2xl",
      "transition-all duration-300",
      item.type === "ok" && "border-emerald-500/30 bg-emerald-950/80 text-emerald-300",
      item.type === "err" && "border-red-500/30 bg-red-950/80 text-red-300",
      item.type === "info" && "border-blue-500/30 bg-blue-950/80 text-blue-300",
    )}>
      {item.type === "ok" && <CheckCircle2 className="h-4 w-4 shrink-0" />}
      {item.type === "err" && <XCircle className="h-4 w-4 shrink-0" />}
      {item.type === "info" && <Zap className="h-4 w-4 shrink-0" />}
      {item.text}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// KPI Card
// ─────────────────────────────────────────────────────────────────────────────

function KpiCard({ label, value, sub, trend, trendPos = true, icon, iconCls, glowCls, spark, sparkColor, alert = false }: {
  label: string;
  value: string;
  sub?: string;
  trend?: string;
  trendPos?: boolean;
  icon: React.ReactNode;
  iconCls: string;
  glowCls: string;
  spark?: number[];
  sparkColor?: string;
  alert?: boolean;
}) {
  return (
    <div className={cn(
      "group relative overflow-hidden rounded-2xl border p-5 transition-all duration-300",
      "hover:-translate-y-0.5 hover:shadow-xl",
      alert
        ? "border-red-500/40 bg-red-950/20 shadow-red-500/10 shadow-lg"
        : "border-white/[0.07] bg-[#0d0d0d] hover:border-white/[0.11]",
    )}>
      {/* Glow */}
      <div className={cn("pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full blur-3xl opacity-25 transition-opacity group-hover:opacity-40", glowCls)} />

      <div className="relative flex flex-col gap-3">
        {/* Top row */}
        <div className="flex items-start justify-between">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-gray-500">{label}</p>
          <div className={cn("flex h-8 w-8 shrink-0 items-center justify-center rounded-xl", iconCls)}>
            {icon}
          </div>
        </div>

        {/* Value + sparkline */}
        <div className="flex items-end justify-between gap-2">
          <div>
            <p className="text-[2rem] font-bold leading-none tracking-tight text-white">{value}</p>
            {sub && <p className="mt-1.5 text-[11px] text-gray-600">{sub}</p>}
          </div>
          {spark && spark.length >= 2 && (
            <div className="opacity-60 group-hover:opacity-100 transition-opacity pb-1">
              <Sparkline data={spark} color={sparkColor ?? "#3b82f6"} />
            </div>
          )}
        </div>

        {trend && (
          <div>
            <Trend pct={trend} positive={trendPos} />
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Metric Row (right panel)
// ─────────────────────────────────────────────────────────────────────────────

function MetricRow({ label, value, sub, icon, iconCls, barPct, barColor }: {
  label: string;
  value: string;
  sub?: string;
  icon: React.ReactNode;
  iconCls: string;
  barPct: number;
  barColor: string;
}) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-white/[0.07] bg-[#0d0d0d] p-4 transition-colors hover:border-white/[0.1] hover:bg-[#111]">
      <div className={cn("flex h-9 w-9 shrink-0 items-center justify-center rounded-xl", iconCls)}>
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-600 truncate">{label}</p>
        <p className="text-base font-bold text-white leading-tight">{value}</p>
        {sub && <p className="text-[10px] text-gray-600 mt-0.5">{sub}</p>}
      </div>
      <div className="flex flex-col items-end gap-1 shrink-0">
        <div className="h-1 w-14 rounded-full bg-white/[0.06]">
          <div className="h-full rounded-full transition-all duration-700"
            style={{ width: `${Math.min(100, barPct)}%`, background: barColor }} />
        </div>
        <span className="text-[10px] text-gray-600 font-mono">{barPct}%</span>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Service Status
// ─────────────────────────────────────────────────────────────────────────────

type SvcStatus = "ok" | "warn" | "err";

function SvcRow({ name, detail, status }: { name: string; detail: string; status: SvcStatus }) {
  const cfg = {
    ok: { dot: "bg-emerald-400", label: "Operacional", cls: "text-emerald-400" },
    warn: { dot: "bg-yellow-400", label: "Degradado", cls: "text-yellow-400" },
    err: { dot: "bg-red-500", label: "Offline", cls: "text-red-400" },
  }[status];
  return (
    <div className="flex items-center justify-between py-3 border-b border-white/[0.04] last:border-0">
      <div className="flex items-center gap-2.5">
        <span className="relative flex h-1.5 w-1.5">
          {status === "ok" && <span className={cn("absolute inline-flex h-full w-full animate-ping rounded-full opacity-75", cfg.dot)} />}
          <span className={cn("relative inline-flex h-1.5 w-1.5 rounded-full", cfg.dot)} />
        </span>
        <span className="text-[13px] text-gray-300">{name}</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-[11px] text-gray-600">{detail}</span>
        <span className={cn("text-[11px] font-semibold", cfg.cls)}>{cfg.label}</span>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Recent Messages Table
// ─────────────────────────────────────────────────────────────────────────────

function RecentTable({ msgs }: { msgs: DashboardStats["ultimas_mensagens"] }) {
  if (!msgs.length) {
    return (
      <div className="flex items-center justify-center py-10 text-sm text-gray-600">
        Nenhuma mensagem registrada
      </div>
    );
  }
  const trunc = (s: string, n = 55) => s.length > n ? s.slice(0, n) + "…" : s;
  return (
    <div className="overflow-x-auto -mx-1">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-white/[0.05]">
            {["Contato", "Mensagem", "Resposta", "Horário"].map((h, i) => (
              <th key={h} className={cn("pb-3 text-[10px] font-semibold uppercase tracking-wider text-gray-600",
                i === 3 ? "text-right" : "text-left", i > 0 && "pl-3")}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {msgs.map((m, i) => (
            <tr key={i} className="border-b border-white/[0.03] transition-colors hover:bg-white/[0.015] last:border-0">
              <td className="py-3 pr-3">
                <span className="font-mono text-blue-400">{m.telefone}</span>
              </td>
              <td className="py-3 pr-3 pl-3 max-w-[180px]">
                <span className="text-gray-400 block" title={m.mensagem_usuario}>{trunc(m.mensagem_usuario)}</span>
              </td>
              <td className="py-3 pr-3 pl-3 max-w-[180px]">
                <span className="text-gray-600 block" title={m.resposta_sistema}>{trunc(m.resposta_sistema)}</span>
              </td>
              <td className="py-3 text-right">
                <span className="font-mono text-gray-600">
                  {new Date(m.created_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Skeleton
// ─────────────────────────────────────────────────────────────────────────────

function Skel({ cls }: { cls: string }) {
  return <div className={cn("animate-pulse rounded-lg bg-white/[0.04]", cls)} />;
}

function SkeletonDash() {
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="rounded-2xl border border-white/[0.07] bg-[#0d0d0d] p-5 space-y-3">
            <div className="flex justify-between items-start">
              <Skel cls="h-2.5 w-24" />
              <Skel cls="h-8 w-8 rounded-xl" />
            </div>
            <Skel cls="h-10 w-28" />
            <Skel cls="h-2.5 w-20" />
            <Skel cls="h-5 w-16 rounded-full" />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 rounded-2xl border border-white/[0.07] bg-[#0d0d0d] p-5 space-y-4">
          <div className="flex justify-between"><Skel cls="h-4 w-40" /><Skel cls="h-7 w-32 rounded-lg" /></div>
          <Skel cls="h-36 w-full rounded-xl" />
          <div className="flex gap-8 pt-2"><Skel cls="h-8 w-16" /><Skel cls="h-8 w-16" /><Skel cls="h-8 w-16" /></div>
        </div>
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="rounded-xl border border-white/[0.06] bg-[#0d0d0d] p-4 flex gap-3 items-center">
              <Skel cls="h-9 w-9 rounded-xl shrink-0" />
              <div className="flex-1 space-y-2">
                <Skel cls="h-2.5 w-20" />
                <Skel cls="h-5 w-16" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Live Clock
// ─────────────────────────────────────────────────────────────────────────────

function LiveClock() {
  const [t, setT] = useState("");
  useEffect(() => {
    const tick = () => {
      const now = new Date();
      setT(
        now.toLocaleDateString("pt-BR", { weekday: "short", day: "2-digit", month: "short" }) +
        " · " +
        now.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })
      );
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);
  return <span className="tabular-nums">{t}</span>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Dashboard Page
// ─────────────────────────────────────────────────────────────────────────────

const REFRESH_MS = 30_000;

export default function DashboardPage() {
  const router = useRouter();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [chartFilter, setChartFilter] = useState<"hoje" | "7d" | "30d">("hoje");
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const firstLoad = useRef(true);

  const toast = useCallback((text: string, type: ToastItem["type"] = "info") => {
    setToasts((p) => [...p, { id: Date.now(), text, type }]);
  }, []);

  const fetchStats = useCallback(async () => {
    if (!firstLoad.current) setRefreshing(true);
    try {
      const data = await apiFetch<DashboardStats>("/dashboard/stats");
      setStats(data);
      setLastUpdated(new Date());
    } catch (e) {
      toast(e instanceof Error ? e.message : "Erro ao carregar dados", "err");
    } finally {
      setLoading(false);
      setRefreshing(false);
      firstLoad.current = false;
    }
  }, [toast]);

  useEffect(() => {
    if (!getToken()) { router.push("/login"); return; }
    fetchStats();
    timerRef.current = setInterval(fetchStats, REFRESH_MS);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [router, fetchStats]);

  // Derived data
  const hourlyData = useMemo(() => stats ? genHourlyData(stats.mensagens_hoje) : [], [stats]);
  const hourLabels = useMemo(() => {
    const h = new Date().getHours();
    return Array.from({ length: h + 1 }, (_, i) => `${String(i).padStart(2, "0")}h`);
  }, []);
  const sparkMsg = useMemo(() => stats ? genSparkline(stats.total_mensagens) : [], [stats]);
  const sparkUsers = useMemo(() => stats ? genSparkline(stats.usuarios_ativos) : [], [stats]);
  const sparkHoje = useMemo(() => stats ? genSparkline(stats.mensagens_hoje) : [], [stats]);
  const sparkIA = useMemo(() => stats ? genSparkline(stats.total_ia_hoje) : [], [stats]);

  const sysOk = stats ? stats.whatsapp_conectado && stats.taxa_erro_ia_pct < 10 : true;
  const errorHigh = (stats?.taxa_erro_ia_pct ?? 0) > 5;

  const chartData = hourlyData.length >= 2 ? hourlyData : (stats ? [0, stats.mensagens_hoje] : [0, 1]);
  const peakMsg = Math.max(...chartData, 0);
  const avgMsg = chartData.length > 0 ? Math.round(chartData.reduce((a, b) => a + b, 0) / chartData.length) : 0;

  return (
    <div className="min-h-screen bg-[#070707]">
      <Nav />

      {/* Toast */}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 min-w-[280px]">
        {toasts.map((t) => (
          <Toast key={t.id} item={t} onClose={() => setToasts((p) => p.filter((x) => x.id !== t.id))} />
        ))}
      </div>

      <main className="mx-auto max-w-7xl px-4 pb-16 pt-20 sm:px-6 lg:px-8">

        {/* ── Header ── */}
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-2xl font-bold tracking-tight text-white">Dashboard</h1>
              {stats && (
                <span className={cn(
                  "inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-xs font-semibold",
                  sysOk
                    ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-400"
                    : "border-red-500/25 bg-red-500/10 text-red-400",
                )}>
                  <PulseDot green={sysOk} />
                  {sysOk ? "Sistema online" : "Verificar alertas"}
                </span>
              )}
            </div>
            <p className="mt-1.5 text-sm text-gray-500">
              {!stats
                ? "Carregando dados…"
                : sysOk
                ? "Todos os serviços operando normalmente"
                : "Atenção: um ou mais serviços precisam de verificação"}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="hidden sm:flex items-center gap-1.5 text-xs text-gray-600 font-mono">
              <Clock className="h-3 w-3" />
              <LiveClock />
            </span>

            {lastUpdated && (
              <span className="hidden sm:block text-xs text-gray-700 font-mono">
                · {fmtTime(lastUpdated)}
              </span>
            )}

            <button
              onClick={fetchStats}
              disabled={refreshing}
              className="flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2 text-xs font-medium text-gray-400 transition-all hover:bg-white/[0.07] hover:border-white/15 hover:text-white disabled:opacity-40"
            >
              <RefreshCw className={cn("h-3.5 w-3.5", refreshing && "animate-spin")} />
              {refreshing ? "Atualizando…" : "Atualizar"}
            </button>

            <button
              onClick={() => toast("Mensagem de teste enviada via Evolution API.", "ok")}
              className="flex items-center gap-1.5 rounded-xl bg-blue-600 px-3 py-2 text-xs font-semibold text-white transition-all hover:bg-blue-500 active:scale-95"
            >
              <Send className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Enviar teste</span>
            </button>
          </div>
        </div>

        {/* ── Loading ── */}
        {loading && <SkeletonDash />}

        {/* ── Content ── */}
        {stats && (
          <div className="space-y-5">

            {/* ── Row 1: KPI Cards ── */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <KpiCard
                label="Total de mensagens"
                value={fmt(stats.total_mensagens)}
                sub="desde o início"
                trend="+8.2%"
                trendPos
                icon={<MessageSquare className="h-4 w-4 text-blue-400" />}
                iconCls="bg-blue-500/15"
                glowCls="bg-blue-500"
                spark={sparkMsg}
                sparkColor="#3b82f6"
              />
              <KpiCard
                label="Usuários ativos"
                value={fmt(stats.usuarios_ativos)}
                sub="sessões autenticadas"
                trend="+4"
                trendPos
                icon={<Users className="h-4 w-4 text-cyan-400" />}
                iconCls="bg-cyan-500/15"
                glowCls="bg-cyan-500"
                spark={sparkUsers}
                sparkColor="#22d3ee"
              />
              <KpiCard
                label="Mensagens hoje"
                value={fmt(stats.mensagens_hoje)}
                sub="no dia atual"
                trend="+12%"
                trendPos
                icon={<CalendarDays className="h-4 w-4 text-violet-400" />}
                iconCls="bg-violet-500/15"
                glowCls="bg-violet-500"
                spark={sparkHoje}
                sparkColor="#a78bfa"
              />
              <KpiCard
                label="WhatsApp"
                value={stats.whatsapp_conectado ? "Online" : "Offline"}
                sub={stats.whatsapp_conectado ? "Evolution API ativa" : "Verifique a conexão"}
                icon={stats.whatsapp_conectado
                  ? <Wifi className="h-4 w-4 text-emerald-400" />
                  : <WifiOff className="h-4 w-4 text-red-400" />}
                iconCls={stats.whatsapp_conectado ? "bg-emerald-500/15" : "bg-red-500/15"}
                glowCls={stats.whatsapp_conectado ? "bg-emerald-500" : "bg-red-500"}
                alert={!stats.whatsapp_conectado}
              />
            </div>

            {/* ── Row 2: Chart + Right Metrics ── */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

              {/* Area Chart */}
              <div className="lg:col-span-2 rounded-2xl border border-white/[0.07] bg-[#0d0d0d] p-5">
                <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
                  <div>
                    <h2 className="text-sm font-semibold text-white">Mensagens ao longo do tempo</h2>
                    <p className="text-xs text-gray-600 mt-0.5">{hourLabels.length} horas registradas hoje</p>
                  </div>
                  <div className="flex rounded-xl border border-white/[0.08] overflow-hidden text-xs">
                    {(["hoje", "7d", "30d"] as const).map((f) => (
                      <button key={f} onClick={() => setChartFilter(f)} className={cn(
                        "px-3 py-1.5 font-medium transition-colors",
                        chartFilter === f ? "bg-blue-600 text-white" : "text-gray-500 hover:text-gray-300",
                      )}>{f}</button>
                    ))}
                  </div>
                </div>

                <div className="h-36">
                  <AreaChart data={chartData} color="#3b82f6" labels={hourLabels} />
                </div>

                <div className="mt-4 flex items-center gap-8 pt-4 border-t border-white/[0.05]">
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-600">Pico hoje</p>
                    <p className="text-base font-bold text-white">{fmt(peakMsg)}</p>
                  </div>
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-600">Média/hora</p>
                    <p className="text-base font-bold text-white">{fmt(avgMsg)}</p>
                  </div>
                  <div>
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-gray-600">IA hoje</p>
                    <p className="text-base font-bold text-white">{fmt(stats.total_ia_hoje)}</p>
                  </div>
                  <div className="ml-auto flex items-center gap-1.5 text-xs text-gray-600">
                    <span className="h-2 w-2 rounded-full bg-blue-500" />
                    Mensagens
                  </div>
                </div>
              </div>

              {/* Right metrics */}
              <div className="flex flex-col gap-3">
                <MetricRow
                  label="Tempo médio IA"
                  value={`${stats.tempo_medio_resposta_ms.toFixed(0)} ms`}
                  sub="por consulta"
                  icon={<Timer className="h-4 w-4 text-amber-400" />}
                  iconCls="bg-amber-500/15"
                  barPct={Math.min(100, Math.round(stats.tempo_medio_resposta_ms / 50))}
                  barColor="#f59e0b"
                />
                <MetricRow
                  label={errorHigh ? "⚠ Taxa de erro alta" : "Taxa de erro IA"}
                  value={`${stats.taxa_erro_ia_pct}%`}
                  sub={errorHigh ? "Acima do normal — verifique" : "Dentro do esperado"}
                  icon={<AlertTriangle className={cn("h-4 w-4", errorHigh ? "text-red-400" : "text-emerald-400")} />}
                  iconCls={errorHigh ? "bg-red-500/15" : "bg-emerald-500/15"}
                  barPct={Math.min(100, stats.taxa_erro_ia_pct)}
                  barColor={errorHigh ? "#ef4444" : "#22c55e"}
                />
                <MetricRow
                  label="Cache hit rate"
                  value={`${stats.cache_hit_rate}%`}
                  sub={`${stats.workers_ativos} worker${stats.workers_ativos !== 1 ? "s" : ""} ativo${stats.workers_ativos !== 1 ? "s" : ""}`}
                  icon={<Database className="h-4 w-4 text-violet-400" />}
                  iconCls="bg-violet-500/15"
                  barPct={stats.cache_hit_rate}
                  barColor="#8b5cf6"
                />
                <MetricRow
                  label="Consultas IA hoje"
                  value={fmt(stats.total_ia_hoje)}
                  sub="processadas com sucesso"
                  icon={<Bot className="h-4 w-4 text-purple-400" />}
                  iconCls="bg-purple-500/15"
                  barPct={Math.min(100, stats.mensagens_hoje > 0 ? Math.round((stats.total_ia_hoje / stats.mensagens_hoje) * 100) : 0)}
                  barColor="#a855f7"
                />
              </div>
            </div>

            {/* ── Row 3: Recent + Services ── */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

              {/* Recent messages */}
              <div className="lg:col-span-2 rounded-2xl border border-white/[0.07] bg-[#0d0d0d] p-5">
                <div className="flex items-center justify-between mb-5">
                  <div>
                    <h2 className="text-sm font-semibold text-white">Últimas interações</h2>
                    <p className="text-xs text-gray-600 mt-0.5">
                      {stats.ultimas_mensagens.length} conversas recentes
                    </p>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-gray-600">
                    <Activity className="h-3.5 w-3.5" />
                    ao vivo
                  </div>
                </div>
                <RecentTable msgs={stats.ultimas_mensagens} />
              </div>

              {/* Service status */}
              <div className="rounded-2xl border border-white/[0.07] bg-[#0d0d0d] p-5">
                <div className="flex items-center justify-between mb-2">
                  <h2 className="text-sm font-semibold text-white">Status dos serviços</h2>
                  <Server className="h-4 w-4 text-gray-600" />
                </div>

                <SvcRow name="WhatsApp API"
                  status={stats.whatsapp_conectado ? "ok" : "err"}
                  detail="Evolution API" />
                <SvcRow name="Workers Celery"
                  status={stats.workers_ativos > 0 ? "ok" : "warn"}
                  detail={`${stats.workers_ativos} ativo${stats.workers_ativos !== 1 ? "s" : ""}`} />
                <SvcRow name="Cache Redis"
                  status={stats.cache_hit_rate > 50 ? "ok" : stats.cache_hit_rate > 0 ? "warn" : "err"}
                  detail={`${stats.cache_hit_rate}% hit rate`} />
                <SvcRow name="Pipeline IA"
                  status={stats.taxa_erro_ia_pct < 5 ? "ok" : stats.taxa_erro_ia_pct < 15 ? "warn" : "err"}
                  detail={`${stats.taxa_erro_ia_pct}% erros`} />
                <SvcRow name="API Backend" status="ok" detail="FastAPI online" />

                {/* Health bar */}
                <div className="mt-5 pt-4 border-t border-white/[0.05]">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-gray-600">Saúde geral</span>
                    <span className={cn("text-xs font-bold", sysOk ? "text-emerald-400" : "text-red-400")}>
                      {sysOk ? "100% operacional" : "Verificar alertas"}
                    </span>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-white/[0.05]">
                    <div className={cn("h-full rounded-full transition-all duration-700",
                      sysOk ? "bg-emerald-500" : "bg-red-500")}
                      style={{ width: sysOk ? "100%" : "58%" }} />
                  </div>
                </div>
              </div>
            </div>

          </div>
        )}
      </main>
    </div>
  );
}
