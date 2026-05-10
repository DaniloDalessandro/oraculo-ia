"use client"

import type { ChartConfig } from "./types"

interface Props {
  config: ChartConfig
}

function formatKpiValue(raw: unknown): string {
  const num = Number(raw)
  if (isNaN(num)) return String(raw ?? "—")

  if (Math.abs(num) >= 1_000_000)
    return (num / 1_000_000).toLocaleString("pt-BR", { maximumFractionDigits: 2 }) + "M"
  if (Math.abs(num) >= 1_000)
    return num.toLocaleString("pt-BR", { maximumFractionDigits: 1 })
  return num.toLocaleString("pt-BR", { maximumFractionDigits: 2 })
}

export function KPICardMessage({ config }: Props) {
  const { data, y_keys, x_key } = config
  const row = data?.[0] ?? {}

  const value = y_keys?.[0] ? row[y_keys[0]] : null
  const label = y_keys?.[0] ?? ""
  const subtitle = x_key && row[x_key] ? String(row[x_key]) : ""

  return (
    <div className="flex flex-col items-center justify-center py-6 gap-1">
      {subtitle && (
        <p className="text-xs text-muted-foreground uppercase tracking-wide">{subtitle}</p>
      )}
      <p className="text-5xl font-bold tabular-nums tracking-tight text-foreground">
        {formatKpiValue(value)}
      </p>
      {label && (
        <p className="text-sm text-muted-foreground mt-1 capitalize">
          {label.replace(/_/g, " ")}
        </p>
      )}
    </div>
  )
}
