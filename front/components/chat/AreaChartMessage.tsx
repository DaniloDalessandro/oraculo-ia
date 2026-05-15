"use client"

import {
  AreaChart,
  Area,
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

export function AreaChartMessage({ config }: Props) {
  const { data, x_key, y_keys } = config

  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
        <defs>
          {y_keys.map((key, i) => (
            <linearGradient key={key} id={`grad-${i}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={CHART_COLORS[i % CHART_COLORS.length]} stopOpacity={0.3} />
              <stop offset="95%" stopColor={CHART_COLORS[i % CHART_COLORS.length]} stopOpacity={0} />
            </linearGradient>
          ))}
        </defs>
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
          <Area
            key={key}
            type="monotone"
            dataKey={key}
            stroke={CHART_COLORS[i % CHART_COLORS.length]}
            strokeWidth={2}
            fill={`url(#grad-${i})`}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  )
}
