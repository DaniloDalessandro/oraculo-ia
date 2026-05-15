"use client"

import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts"
import { CHART_COLORS, GRID_COLOR, TICK_COLOR, TOOLTIP_STYLE } from "./chart-colors"
import type { ChartConfig } from "./types"

interface Props {
  config: ChartConfig
}

export function ComposedChartMessage({ config }: Props) {
  const { data, x_key, y_keys } = config
  // First y_key as Bar, rest as Lines
  const [barKey, ...lineKeys] = y_keys

  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} />
        <XAxis
          dataKey={x_key}
          tick={{ fontSize: 11, fill: TICK_COLOR }}
          tickLine={false}
          axisLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          tick={{ fontSize: 11, fill: TICK_COLOR }}
          tickLine={false}
          axisLine={false}
          width={60}
        />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {barKey && (
          <Bar
            dataKey={barKey}
            fill={CHART_COLORS[0]}
            radius={[4, 4, 0, 0]}
            opacity={0.85}
          />
        )}
        {lineKeys.map((key, i) => (
          <Line
            key={key}
            type="monotone"
            dataKey={key}
            stroke={CHART_COLORS[i + 1] ?? CHART_COLORS[1]}
            strokeWidth={2}
            dot={{ r: 3 }}
          />
        ))}
      </ComposedChart>
    </ResponsiveContainer>
  )
}
