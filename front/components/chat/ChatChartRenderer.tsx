"use client"

import { useRef, useState } from "react"
import { BarChart2, Table, AlertTriangle, Download, Copy, Check } from "lucide-react"
import { Button } from "@/components/ui/button"
import { BarChartMessage } from "./BarChartMessage"
import { HorizontalBarChartMessage } from "./HorizontalBarChartMessage"
import { KPICardMessage } from "./KPICardMessage"
import { LineChartMessage } from "./LineChartMessage"
import { PieChartMessage } from "./PieChartMessage"
import { AreaChartMessage } from "./AreaChartMessage"
import { ComposedChartMessage } from "./ComposedChartMessage"
import { ChartTableFallback } from "./ChartTableFallback"
import type { ChartConfig } from "./types"

interface Props {
  config: ChartConfig
}

export function ChatChartRenderer({ config }: Props) {
  const [showTable, setShowTable] = useState(false)
  const [copied, setCopied] = useState(false)
  const chartRef = useRef<HTMLDivElement>(null)

  const captureChart = (): Promise<Blob | null> =>
    new Promise((resolve) => {
      const container = chartRef.current
      if (!container) return resolve(null)

      // KPI e tabela não têm SVG — captura via html2canvas
      const svg = container.querySelector("svg")
      if (!svg) {
        import("html2canvas").then(({ default: html2canvas }) => {
          html2canvas(container, { scale: 2, backgroundColor: "#ffffff" }).then((canvas) => {
            canvas.toBlob((b) => resolve(b), "image/png")
          }).catch(() => resolve(null))
        }).catch(() => resolve(null))
        return
      }

      const { width, height } = svg.getBoundingClientRect()
      const scale = 2

      // Clonar SVG e injetar estilos computados inline para fidelidade visual
      const clone = svg.cloneNode(true) as SVGElement
      clone.setAttribute("xmlns", "http://www.w3.org/2000/svg")
      clone.setAttribute("width", String(width))
      clone.setAttribute("height", String(height))

      // Fundo branco explícito
      const bg = document.createElementNS("http://www.w3.org/2000/svg", "rect")
      bg.setAttribute("width", "100%")
      bg.setAttribute("height", "100%")
      bg.setAttribute("fill", "white")
      clone.insertBefore(bg, clone.firstChild)

      const svgStr = new XMLSerializer().serializeToString(clone)
      const blob = new Blob([svgStr], { type: "image/svg+xml" })
      const url = URL.createObjectURL(blob)

      const img = new Image()
      img.onload = () => {
        const canvas = document.createElement("canvas")
        canvas.width = width * scale
        canvas.height = height * scale
        const ctx = canvas.getContext("2d")!
        ctx.fillStyle = "#ffffff"
        ctx.fillRect(0, 0, canvas.width, canvas.height)
        ctx.scale(scale, scale)
        ctx.drawImage(img, 0, 0)
        URL.revokeObjectURL(url)
        canvas.toBlob((b) => resolve(b), "image/png")
      }
      img.onerror = () => { URL.revokeObjectURL(url); resolve(null) }
      img.src = url
    })

  const handleDownload = async () => {
    const blob = await captureChart()
    if (!blob) return
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.download = `${config.title ?? "grafico"}.png`
    link.href = url
    link.click()
    URL.revokeObjectURL(url)
  }

  const handleCopy = async () => {
    const blob = await captureChart()
    if (!blob) return
    await navigator.clipboard.write([new ClipboardItem({ "image/png": blob })])
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  if (!config.should_render) {
    return null
  }

  if (!config.data || config.data.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-2">
        Gráfico solicitado, mas sem dados suficientes.
      </p>
    )
  }

  return (
    <div className="mt-3 rounded-xl border bg-card p-4 space-y-2">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          {config.title && (
            <p className="text-sm font-semibold leading-tight">{config.title}</p>
          )}
          {config.description && (
            <p className="text-xs text-muted-foreground mt-0.5">{config.description}</p>
          )}
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-xs gap-1"
            onClick={() => setShowTable((v) => !v)}
          >
            {showTable ? (
              <><BarChart2 className="size-3.5" /> Gráfico</>
            ) : (
              <><Table className="size-3.5" /> Tabela</>
            )}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 w-7 p-0"
            onClick={handleDownload}
            title="Baixar imagem"
          >
            <Download className="size-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 w-7 p-0"
            onClick={handleCopy}
            title="Copiar imagem"
          >
            {copied ? (
              <Check className="size-3.5 text-emerald-500" />
            ) : (
              <Copy className="size-3.5" />
            )}
          </Button>
        </div>
      </div>

      {/* Warnings */}
      {config.warnings && config.warnings.length > 0 && (
        <div className="flex items-start gap-1.5 text-xs text-amber-600 dark:text-amber-400">
          <AlertTriangle className="size-3.5 mt-0.5 shrink-0" />
          <span>{config.warnings[0]}</span>
        </div>
      )}

      {/* Chart or Table */}
      <div ref={chartRef}>
        {showTable ? (
          <ChartTableFallback config={config} />
        ) : (
          <ChartSwitch config={config} />
        )}
      </div>

      {/* Point count */}
      <p className="text-[11px] text-muted-foreground text-right">
        {config.data.length} {config.data.length === 1 ? "ponto" : "pontos"} de dados
      </p>
    </div>
  )
}

function ChartSwitch({ config }: { config: ChartConfig }) {
  switch (config.type) {
    case "bar":
      return <BarChartMessage config={config} />
    case "horizontal_bar":
      return <HorizontalBarChartMessage config={config} />
    case "kpi":
      return <KPICardMessage config={config} />
    case "line":
      return <LineChartMessage config={config} />
    case "pie":
      return <PieChartMessage config={config} />
    case "area":
      return <AreaChartMessage config={config} />
    case "composed":
      return <ComposedChartMessage config={config} />
    case "table":
      return <ChartTableFallback config={config} />
    default:
      return <BarChartMessage config={config} />
  }
}
