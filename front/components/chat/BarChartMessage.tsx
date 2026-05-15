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
import { CHART_COLORS, GRID_COLOR, TICK_COLOR, TOOLTIP_STYLE } from "./chart-colors"
import type { ChartConfig } from "./types"

interface Props {
  config: ChartConfig
}

export function BarChartMessage({ config }: Props) {
  const { data, x_key, y_keys } = config

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
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
        {y_keys.length > 1 && <Legend wrapperStyle={{ fontSize: 12 }} />}
        {y_keys.map((key, i) => (
          <Bar
            key={key}
            dataKey={key}
            fill={CHART_COLORS[i % CHART_COLORS.length]}
            radius={[4, 4, 0, 0]}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  )
}
