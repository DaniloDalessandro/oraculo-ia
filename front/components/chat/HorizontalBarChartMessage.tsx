"use client"

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts"
import { CHART_COLORS, GRID_COLOR, TICK_COLOR } from "./chart-colors"
import type { ChartConfig } from "./types"

interface Props {
  config: ChartConfig
}

export function HorizontalBarChartMessage({ config }: Props) {
  const { data, x_key, y_keys } = config

  // Altura dinâmica baseada no número de barras
  const height = Math.max(240, Math.min(data.length * 36 + 40, 520))

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 4, right: 24, left: 8, bottom: 4 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} horizontal={false} />
        <XAxis
          type="number"
          tick={{ fontSize: 11, fill: TICK_COLOR }}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          type="category"
          dataKey={x_key}
          tick={{ fontSize: 11, fill: TICK_COLOR }}
          tickLine={false}
          axisLine={false}
          width={120}
        />
        <Tooltip
          contentStyle={{
            fontSize: 12,
            borderRadius: 8,
            border: "1px solid hsl(var(--border))",
            background: "hsl(var(--popover))",
            color: "hsl(var(--popover-foreground))",
          }}
        />
        {y_keys.length > 1 && <Legend wrapperStyle={{ fontSize: 12 }} />}
        {y_keys.map((key, i) => (
          <Bar
            key={key}
            dataKey={key}
            fill={CHART_COLORS[i % CHART_COLORS.length]}
            radius={[0, 4, 4, 0]}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  )
}
