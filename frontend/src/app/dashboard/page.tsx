"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Nav from "@/components/Nav";
import { apiFetch, getToken, type DashboardStats } from "@/lib/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Progress,
  ProgressTrack,
  ProgressIndicator,
  ProgressLabel,
  ProgressValue,
} from "@/components/ui/progress";
import {
  MessageSquare,
  Users,
  CalendarDays,
  Wifi,
  WifiOff,
  Bot,
  Timer,
  AlertTriangle,
  Database,
  Loader2,
  Clock,
} from "lucide-react";

// ── Helpers ──────────────────────────────────────────────────────────────────


function formatTime(date: Date) {
  return date.toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

const REFRESH_INTERVAL = 30_000;

// ── KPI Card ──────────────────────────────────────────────────────────────────

interface KpiCardProps {
  label: string;
  value: string | number;
  sub?: string;
  icon: React.ReactNode;
  iconBg?: string;
  badge?: React.ReactNode;
}

function KpiCard({ label, value, sub, icon, iconBg = "bg-zinc-800", badge }: KpiCardProps) {
  return (
    <Card>
      <CardHeader className="pb-0">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            {label}
          </CardTitle>
          <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${iconBg}`}>
            {icon}
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-2">
        <p className="text-3xl font-bold tracking-tight">{value}</p>
        {sub && (
          <p className="mt-1 text-xs text-muted-foreground">{sub}</p>
        )}
        {badge && <div className="mt-2">{badge}</div>}
      </CardContent>
    </Card>
  );
}

// ── WhatsApp Status Card ──────────────────────────────────────────────────────

function WhatsAppCard({ connected }: { connected: boolean }) {
  return (
    <Card>
      <CardHeader className="pb-0">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            WhatsApp
          </CardTitle>
          <div
            className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${
              connected ? "bg-emerald-500/15" : "bg-red-500/15"
            }`}
          >
            {connected ? (
              <Wifi className="h-4 w-4 text-emerald-400" />
            ) : (
              <WifiOff className="h-4 w-4 text-red-400" />
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-2">
        <div className="flex items-center gap-2">
          {/* Pulse dot */}
          <span className="relative flex h-2.5 w-2.5">
            {connected && (
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
            )}
            <span
              className={`relative inline-flex h-2.5 w-2.5 rounded-full ${
                connected ? "bg-emerald-400" : "bg-red-500"
              }`}
            />
          </span>
          <p className="text-3xl font-bold tracking-tight">
            {connected ? "Online" : "Offline"}
          </p>
        </div>
        <p className="mt-1 text-xs text-muted-foreground">
          {connected ? "Evolution API ativa" : "Verifique a conexão"}
        </p>
        <div className="mt-2">
          <Badge variant={connected ? "secondary" : "destructive"} className={connected ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/20" : ""}>
            {connected ? "Conectado" : "Desconectado"}
          </Badge>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Cache Progress Card ───────────────────────────────────────────────────────

function CacheCard({ hitRate, workersAtivos }: { hitRate: number; workersAtivos: number }) {
  return (
    <Card>
      <CardHeader className="pb-0">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Cache hit rate
          </CardTitle>
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-violet-500/15">
            <Database className="h-4 w-4 text-violet-400" />
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-2">
        <p className="text-3xl font-bold tracking-tight">{hitRate}%</p>
        <p className="mt-1 text-xs text-muted-foreground">
          {workersAtivos} worker{workersAtivos !== 1 ? "s" : ""} ativo{workersAtivos !== 1 ? "s" : ""}
        </p>
        <div className="mt-3">
          <Progress value={hitRate} className="gap-1.5">
            <div className="flex w-full items-center justify-between">
              <ProgressLabel className="text-xs text-muted-foreground">Cache</ProgressLabel>
              <ProgressValue className="text-xs text-muted-foreground" />
            </div>
            <ProgressTrack className="bg-zinc-800">
              <ProgressIndicator className="bg-violet-500" />
            </ProgressTrack>
          </Progress>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Error Rate Card ───────────────────────────────────────────────────────────

function ErrorRateCard({ pct }: { pct: number }) {
  const isHigh = pct > 10;
  return (
    <Card>
      <CardHeader className="pb-0">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Taxa de erro IA
          </CardTitle>
          <div
            className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${
              isHigh ? "bg-red-500/15" : "bg-emerald-500/15"
            }`}
          >
            <AlertTriangle
              className={`h-4 w-4 ${isHigh ? "text-red-400" : "text-emerald-400"}`}
            />
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-2">
        <p className="text-3xl font-bold tracking-tight">{pct}%</p>
        <p className="mt-1 text-xs text-muted-foreground">consultas com falha</p>
        <div className="mt-2">
          <Badge
            variant={isHigh ? "destructive" : "secondary"}
            className={
              isHigh
                ? ""
                : "bg-emerald-500/15 text-emerald-400 border-emerald-500/20"
            }
          >
            {isHigh ? "Alto" : "Normal"}
          </Badge>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Skeleton grid ─────────────────────────────────────────────────────────────

function SkeletonGrid() {
  return (
    <>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i}>
            <CardHeader className="pb-0">
              <div className="flex items-start justify-between">
                <Skeleton className="h-3 w-28" />
                <Skeleton className="h-8 w-8 rounded-lg" />
              </div>
            </CardHeader>
            <CardContent className="pt-2">
              <Skeleton className="h-9 w-20" />
              <Skeleton className="mt-2 h-3 w-32" />
            </CardContent>
          </Card>
        ))}
      </div>
      <div className="mt-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i}>
            <CardHeader className="pb-0">
              <div className="flex items-start justify-between">
                <Skeleton className="h-3 w-24" />
                <Skeleton className="h-8 w-8 rounded-lg" />
              </div>
            </CardHeader>
            <CardContent className="pt-2">
              <Skeleton className="h-9 w-20" />
              <Skeleton className="mt-2 h-3 w-28" />
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const router = useRouter();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isFirstLoad = useRef(true);

  const fetchStats = useCallback(async () => {
    if (!isFirstLoad.current) setRefreshing(true);
    try {
      const data = await apiFetch<DashboardStats>("/dashboard/stats");
      setStats(data);
      setLastUpdated(new Date());
      setError("");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Erro ao carregar dados");
    } finally {
      setLoading(false);
      setRefreshing(false);
      isFirstLoad.current = false;
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
    <div className="min-h-screen bg-background">
      <Nav />

      <main className="mx-auto max-w-7xl px-4 pb-12 pt-20 sm:px-6 lg:px-8">

        {/* Page header */}
        <div className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Visão geral do sistema em tempo real
            </p>
          </div>

          <div className="flex items-center gap-2">
            {refreshing && (
              <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Atualizando…
              </span>
            )}
            {lastUpdated && (
              <Badge variant="outline" className="gap-1.5 font-mono text-xs">
                <Clock className="h-3 w-3" />
                Atualizado às {formatTime(lastUpdated)}
              </Badge>
            )}
          </div>
        </div>

        {/* Error state */}
        {error && (
          <div className="mb-6 flex items-center gap-3 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            {error}
          </div>
        )}

        {/* Loading skeleton */}
        {loading && <SkeletonGrid />}

        {/* Main content */}
        {stats && (
          <>
            {/* Row 1 — Core KPIs */}
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              <KpiCard
                label="Total mensagens"
                value={stats.total_mensagens.toLocaleString("pt-BR")}
                sub="desde o início"
                icon={<MessageSquare className="h-4 w-4 text-blue-400" />}
                iconBg="bg-blue-500/15"
              />
              <KpiCard
                label="Usuários ativos"
                value={stats.usuarios_ativos.toLocaleString("pt-BR")}
                sub="com interação"
                icon={<Users className="h-4 w-4 text-sky-400" />}
                iconBg="bg-sky-500/15"
              />
              <KpiCard
                label="Mensagens hoje"
                value={stats.mensagens_hoje.toLocaleString("pt-BR")}
                sub="no dia atual"
                icon={<CalendarDays className="h-4 w-4 text-indigo-400" />}
                iconBg="bg-indigo-500/15"
              />
              <WhatsAppCard connected={stats.whatsapp_conectado} />
            </div>

            {/* Row 2 — IA metrics */}
            <div className="mt-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
              <KpiCard
                label="IA hoje"
                value={stats.total_ia_hoje.toLocaleString("pt-BR")}
                sub="consultas processadas"
                icon={<Bot className="h-4 w-4 text-purple-400" />}
                iconBg="bg-purple-500/15"
              />
              <KpiCard
                label="Tempo médio IA"
                value={`${stats.tempo_medio_resposta_ms.toFixed(0)} ms`}
                sub="por consulta"
                icon={<Timer className="h-4 w-4 text-amber-400" />}
                iconBg="bg-amber-500/15"
              />
              <ErrorRateCard pct={stats.taxa_erro_ia_pct} />
              <CacheCard
                hitRate={stats.cache_hit_rate}
                workersAtivos={stats.workers_ativos}
              />
            </div>

          </>
        )}
      </main>
    </div>
  );
}
