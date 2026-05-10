"use client"

import type { ChartConfig } from "./types"

interface Props {
  config: ChartConfig
}

export function ChartTableFallback({ config }: Props) {
  const { data, x_key, y_keys } = config
  const allKeys = x_key ? [x_key, ...y_keys] : y_keys

  if (!data || data.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4 text-center">
        Nenhum dado disponível.
      </p>
    )
  }

  return (
    <div className="overflow-x-auto rounded-md border text-sm">
      <table className="w-full text-left">
        <thead className="bg-muted/50">
          <tr>
            {allKeys.map((key) => (
              <th
                key={key}
                className="px-3 py-2 font-medium text-muted-foreground whitespace-nowrap"
              >
                {key}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i} className="border-t hover:bg-muted/30 transition-colors">
              {allKeys.map((key) => (
                <td key={key} className="px-3 py-2 whitespace-nowrap">
                  {row[key] != null ? String(row[key]) : "—"}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
