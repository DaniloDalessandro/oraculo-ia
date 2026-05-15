"use client"

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts"
import { CHART_COLORS, TOOLTIP_STYLE } from "./chart-colors"
import type { ChartConfig } from "./types"

interface Props {
  config: ChartConfig
}

export function PieChartMessage({ config }: Props) {
  const { data, x_key, y_keys } = config
  const valueKey = y_keys[0] ?? ""

  return (
    <ResponsiveContainer width="100%" height={280}>
      <PieChart>
        <Pie
          data={data}
          dataKey={valueKey}
          nameKey={x_key}
          cx="50%"
          cy="50%"
          outerRadius={100}
          label={({ name, percent }: { name?: string; percent?: number }) =>
            (percent ?? 0) > 0.04 ? `${name ?? ""} (${((percent ?? 0) * 100).toFixed(0)}%)` : ""
          }
          labelLine={false}
        >
          {data.map((_, i) => (
            <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          formatter={(value) => [(value as number).toLocaleString("pt-BR"), valueKey]}
        />
        <Legend
          wrapperStyle={{ fontSize: 12 }}
          formatter={(value) => String(value).slice(0, 20)}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}
