"use client"

import { useEffect, useState, useCallback } from "react"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { Separator } from "@/components/ui/separator"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"

interface TableMeta {
  name: string
  columns: { name: string }[]
}

interface TableDataResult {
  columns: string[]
  rows: Record<string, string | null>[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export default function DadosPage() {
  // Schema
  const [tables, setTables] = useState<TableMeta[]>([])
  const [schemaLoading, setSchemaLoading] = useState(true)

  // Selected table + data
  const [selectedTable, setSelectedTable] = useState<string>("")
  const [search, setSearch] = useState("")
  const [page, setPage] = useState(1)
  const [data, setData] = useState<TableDataResult | null>(null)
  const [dataLoading, setDataLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load schema once
  useEffect(() => {
    fetch("/api/schema")
      .then((r) => r.json())
      .then((d) => {
        if (d.tables) {
          setTables(d.tables)
          if (d.tables.length > 0) setSelectedTable(d.tables[0].name)
        }
      })
      .finally(() => setSchemaLoading(false))
  }, [])

  // Load table data
  const loadData = useCallback((table: string, pg: number, q: string) => {
    if (!table) return
    setDataLoading(true)
    setError(null)
    const params = new URLSearchParams({ table, page: String(pg), page_size: "50" })
    if (q) params.set("search", q)
    fetch(`/api/table-data?${params}`)
      .then((r) => r.json())
      .then((d) => {
        if (d.error) setError(d.error)
        else setData(d)
      })
      .catch(() => setError("Falha na conexão."))
      .finally(() => setDataLoading(false))
  }, [])

  useEffect(() => {
    if (selectedTable) {
      setPage(1)
      setData(null)
      setSearch("")
    }
  }, [selectedTable])

  useEffect(() => {
    if (selectedTable) loadData(selectedTable, page, search)
  }, [selectedTable, page, loadData]) // eslint-disable-line

  // Search with debounce
  useEffect(() => {
    if (!selectedTable) return
    const t = setTimeout(() => {
      setPage(1)
      loadData(selectedTable, 1, search)
    }, 400)
    return () => clearTimeout(t)
  }, [search]) // eslint-disable-line

  const currentTable = tables.find((t) => t.name === selectedTable)

  return (
    <div className="flex flex-col h-full min-h-svh">
      <header className="flex h-14 shrink-0 items-center gap-3 px-4 border-b border-white/8">
        <SidebarTrigger className="text-white/50 hover:text-white transition-colors" />
        <Separator orientation="vertical" className="h-4 bg-white/10 data-vertical:h-4 data-vertical:self-auto" />
        <span className="text-sm font-medium text-white/60">Dados</span>
      </header>

      <div className="flex flex-col flex-1 overflow-hidden p-6 gap-4">
        {/* Title */}
        <div className="space-y-1 shrink-0">
          <h1 className="text-white" style={{ fontSize: "35px", fontWeight: 300 }}>Dados</h1>
          <p className="text-white/40 text-sm">Explorador de tabelas operacionais</p>
        </div>

        {schemaLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-9 w-full rounded-md bg-white/5" />
            ))}
          </div>
        ) : (
          <>
            {/* Filters bar */}
            <div className="flex flex-wrap gap-3 items-center shrink-0">
              <select
                value={selectedTable}
                onChange={(e) => setSelectedTable(e.target.value)}
                className="h-9 rounded-md border border-white/10 bg-[#121314] px-3 text-sm text-white/80 focus:outline-none focus:ring-1 focus:ring-[#0070d1]"
              >
                {tables.map((t) => (
                  <option key={t.name} value={t.name}>{t.name}</option>
                ))}
              </select>

              <Input
                placeholder="Buscar..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="h-9 w-52 bg-[#121314] border-white/10 text-white/80 placeholder:text-white/30 focus-visible:ring-[#0070d1]"
              />

              {data && (
                <span className="ml-auto text-xs text-white/30">
                  {data.total.toLocaleString("pt-BR")} linhas
                  {currentTable && ` · ${currentTable.columns.length} colunas`}
                </span>
              )}
            </div>

            {error && (
              <div className="rounded-lg bg-red-500/10 border border-red-500/20 p-4 text-sm text-red-400 shrink-0">{error}</div>
            )}

            {/* Table container */}
            <div className="flex-1 rounded-lg border border-white/8 overflow-auto min-h-0">
              {dataLoading ? (
                <div className="p-4 space-y-2">
                  {Array.from({ length: 10 }).map((_, i) => (
                    <Skeleton key={i} className="h-8 w-full rounded bg-white/5" />
                  ))}
                </div>
              ) : data && data.rows.length > 0 ? (
                <table className="w-full text-sm border-collapse">
                  <thead className="sticky top-0 z-10">
                    <tr className="bg-[#0d0e0f] border-b border-white/8">
                      <th className="px-3 py-2.5 text-left text-xs font-medium text-white/30 w-10 shrink-0">#</th>
                      {data.columns.map((col) => (
                        <th key={col} className="px-3 py-2.5 text-left text-xs font-medium text-white/50 whitespace-nowrap">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.rows.map((row, i) => (
                      <tr key={i} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                        <td className="px-3 py-2 text-white/20 text-xs">
                          {(data.page - 1) * data.page_size + i + 1}
                        </td>
                        {data.columns.map((col) => (
                          <td key={col} className="px-3 py-2 text-white/70 text-xs whitespace-nowrap max-w-xs truncate">
                            {row[col] === null ? (
                              <span className="text-white/20 italic">null</span>
                            ) : (
                              row[col]
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : !dataLoading && data?.rows.length === 0 ? (
                <div className="flex items-center justify-center h-40 text-white/30 text-sm">
                  Nenhum registro encontrado.
                </div>
              ) : null}
            </div>

            {/* Pagination */}
            {data && data.total_pages > 1 && (
              <div className="flex items-center justify-between shrink-0 pt-1">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1 || dataLoading}
                  className="h-8 px-3 rounded-md text-sm border border-white/10 text-white/50 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  ← Anterior
                </button>
                <span className="text-xs text-white/30">
                  Página {data.page} de {data.total_pages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
                  disabled={page === data.total_pages || dataLoading}
                  className="h-8 px-3 rounded-md text-sm border border-white/10 text-white/50 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  Próxima →
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
