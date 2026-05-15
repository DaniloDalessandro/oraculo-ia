"use client"

import { useEffect, useState, useCallback, useRef } from "react"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { Separator } from "@/components/ui/separator"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"

// ─── Types ────────────────────────────────────────────────────────────────────

interface Atracacao {
  id: number
  operacaomodalid: number
  numero_atracacao: number | null
  status: string | null
  berco: string | null
  navio: string | null
  imo: string | null
  comprimento: string | null
  largura: string | null
  dwt: string | null
  duv: string | null
  escala: string | null
  bordo: string | null
  calado_entrada: string | null
  calado_saida: string | null
  navegacao: string | null
  agencia: string | null
  procedencia: string | null
  destino: string | null
  bandeira: string | null
  eta: string | null
  etb: string | null
  nor: string | null
  prontidao: string | null
  atracacao: string | null
  inicio_operacao: string | null
  termino_operacao: string | null
  desatracacao: string | null
  ets: string | null
  entremanobra: string | null
  is_improdutividade: boolean | null
  horas_planejadas: string | null
  prancha: string | null
  excludente_emap: string | null
  excludente_intemperie: string | null
  excl_emap_lm: string | null
  excl_intemperie_lm: string | null
  prox_atracacao: string | null
}

interface ListResponse {
  results: Atracacao[]
  total: number
  page: number
  page_size: number
  total_pages: number
  bercos: string[]
  statuses: string[]
}

type FormData = Partial<Omit<Atracacao, "id">>

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmtDate(iso: string | null) {
  if (!iso) return "—"
  try {
    return new Date(iso).toLocaleString("pt-BR", {
      day: "2-digit", month: "2-digit", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    })
  } catch {
    return iso
  }
}

function toInputDatetime(iso: string | null) {
  if (!iso) return ""
  return iso.slice(0, 16)
}

function fromInputDatetime(v: string) {
  return v ? `${v}:00Z` : null
}

// ─── Form Field Component ─────────────────────────────────────────────────────

function FormField({
  label, name, type = "text", value, onChange, required,
}: {
  label: string
  name: string
  type?: string
  value: string | number | boolean | null | undefined
  onChange: (name: string, value: string | boolean | null) => void
  required?: boolean
}) {
  const inputClass =
    "h-8 w-full rounded border border-white/10 bg-[#1a1b1c] px-2.5 text-xs text-white/80 placeholder:text-white/20 focus:outline-none focus:ring-1 focus:ring-[#0070d1]"

  if (type === "checkbox") {
    return (
      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={!!value}
          onChange={(e) => onChange(name, e.target.checked)}
          className="w-3.5 h-3.5 accent-[#0070d1]"
        />
        <span className="text-xs text-white/60">{label}</span>
      </label>
    )
  }

  return (
    <div className="flex flex-col gap-1">
      <label className="text-[11px] text-white/40 font-medium">{label}{required && <span className="text-red-400 ml-0.5">*</span>}</label>
      <input
        type={type}
        value={type === "datetime-local" ? toInputDatetime(value as string | null) : (value ?? "") as string | number}
        onChange={(e) =>
          onChange(name, type === "datetime-local" ? fromInputDatetime(e.target.value) : e.target.value)
        }
        required={required}
        className={inputClass}
      />
    </div>
  )
}

// ─── Empty form ───────────────────────────────────────────────────────────────

function emptyForm(): FormData {
  return {
    operacaomodalid: undefined,
    numero_atracacao: undefined,
    status: "",
    berco: "",
    navio: "",
    imo: "",
    dwt: "",
    comprimento: "",
    largura: "",
    bordo: "",
    calado_entrada: "",
    calado_saida: "",
    bandeira: "",
    navegacao: "",
    agencia: "",
    procedencia: "",
    destino: "",
    eta: null,
    etb: null,
    nor: null,
    prontidao: null,
    atracacao: null,
    inicio_operacao: null,
    termino_operacao: null,
    desatracacao: null,
    ets: null,
    horas_planejadas: "",
    prancha: "",
    is_improdutividade: false,
  }
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AtracacoesPage() {
  const [data, setData] = useState<ListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [bercoFilter, setBercoFilter] = useState("")
  const [statusFilter, setStatusFilter] = useState("")
  const [page, setPage] = useState(1)
  const [error, setError] = useState<string | null>(null)

  // Sheet (form)
  const [sheetOpen, setSheetOpen] = useState(false)
  const [editing, setEditing] = useState<Atracacao | null>(null)
  const [form, setForm] = useState<FormData>(emptyForm())
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Delete confirmation
  const [deleteId, setDeleteId] = useState<number | null>(null)
  const [deleting, setDeleting] = useState(false)

  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const load = useCallback((pg: number, q: string, berco: string, st: string) => {
    setLoading(true)
    setError(null)
    const params = new URLSearchParams({ page: String(pg), page_size: "50" })
    if (q) params.set("search", q)
    if (berco) params.set("berco", berco)
    if (st) params.set("status", st)
    fetch(`/api/atracacoes?${params}`)
      .then((r) => r.json())
      .then((d) => {
        if (d.error) setError(d.error)
        else setData(d)
      })
      .catch(() => setError("Falha na conexão."))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load(page, search, bercoFilter, statusFilter)
  }, [page, bercoFilter, statusFilter]) // eslint-disable-line

  useEffect(() => {
    if (searchTimer.current) clearTimeout(searchTimer.current)
    searchTimer.current = setTimeout(() => {
      setPage(1)
      load(1, search, bercoFilter, statusFilter)
    }, 400)
    return () => { if (searchTimer.current) clearTimeout(searchTimer.current) }
  }, [search]) // eslint-disable-line

  function openCreate() {
    setEditing(null)
    setForm(emptyForm())
    setFormError(null)
    setSheetOpen(true)
  }

  function openEdit(row: Atracacao) {
    setEditing(row)
    setForm({ ...row })
    setFormError(null)
    setSheetOpen(true)
  }

  function handleField(name: string, value: string | boolean | null) {
    setForm((prev) => ({ ...prev, [name]: value === "" ? null : value }))
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setFormError(null)
    try {
      const url = editing ? `/api/atracacoes/${editing.id}` : "/api/atracacoes"
      const method = editing ? "PATCH" : "POST"
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      })
      const body = await res.json()
      if (!res.ok) {
        const msg = typeof body === "object"
          ? Object.entries(body).map(([k, v]) => `${k}: ${(v as string[]).join(", ")}`).join(" | ")
          : "Erro ao salvar."
        setFormError(msg)
        return
      }
      setSheetOpen(false)
      load(page, search, bercoFilter, statusFilter)
    } catch {
      setFormError("Falha na conexão.")
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: number) {
    setDeleting(true)
    try {
      await fetch(`/api/atracacoes/${id}`, { method: "DELETE" })
      setDeleteId(null)
      load(page, search, bercoFilter, statusFilter)
    } catch {
      // silent
    } finally {
      setDeleting(false)
    }
  }

  const bercos = data?.bercos ?? []
  const statuses = data?.statuses ?? []

  return (
    <div className="flex flex-col h-full min-h-svh">
      {/* Header */}
      <header className="flex h-14 shrink-0 items-center gap-3 px-4 border-b border-white/8">
        <SidebarTrigger className="text-white/50 hover:text-white transition-colors" />
        <Separator orientation="vertical" className="h-4 bg-white/10 data-vertical:h-4 data-vertical:self-auto" />
        <span className="text-sm font-medium text-white/60">Atracações</span>
      </header>

      <div className="flex flex-col flex-1 overflow-hidden p-6 gap-4">
        {/* Title + actions */}
        <div className="flex items-end justify-between gap-4 shrink-0">
          <div className="space-y-1">
            <h1 className="text-white" style={{ fontSize: "35px", fontWeight: 300 }}>Atracações</h1>
            <p className="text-white/40 text-sm">
              {data ? `${data.total.toLocaleString("pt-BR")} registros` : "Carregando..."}
            </p>
          </div>
          <Button
            onClick={openCreate}
            className="h-9 px-4 bg-[#0070d1] hover:bg-[#0060b8] text-white text-sm rounded-lg shrink-0"
          >
            + Nova atracação
          </Button>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3 items-center shrink-0">
          <Input
            placeholder="Buscar navio, IMO, berço, agência..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-9 w-72 bg-[#121314] border-white/10 text-white/80 placeholder:text-white/30 focus-visible:ring-[#0070d1]"
          />
          <select
            value={bercoFilter}
            onChange={(e) => { setBercoFilter(e.target.value); setPage(1) }}
            className="h-9 rounded-md border border-white/10 bg-[#121314] px-3 text-sm text-white/70 focus:outline-none focus:ring-1 focus:ring-[#0070d1]"
          >
            <option value="">Todos os berços</option>
            {bercos.map((b) => <option key={b} value={b}>{b}</option>)}
          </select>
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
            className="h-9 rounded-md border border-white/10 bg-[#121314] px-3 text-sm text-white/70 focus:outline-none focus:ring-1 focus:ring-[#0070d1]"
          >
            <option value="">Todos os status</option>
            {statuses.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>

        {error && (
          <div className="rounded-lg bg-red-500/10 border border-red-500/20 p-4 text-sm text-red-400 shrink-0">{error}</div>
        )}

        {/* Table */}
        <div className="flex-1 rounded-lg border border-white/8 overflow-auto min-h-0">
          {loading ? (
            <div className="p-4 space-y-2">
              {Array.from({ length: 12 }).map((_, i) => (
                <Skeleton key={i} className="h-8 w-full rounded bg-white/5" />
              ))}
            </div>
          ) : data && data.results.length > 0 ? (
            <table className="w-full text-sm border-collapse">
              <thead className="sticky top-0 z-10">
                <tr className="bg-[#0d0e0f] border-b border-white/8">
                  {["ID Modal", "Navio", "Berço", "Status", "DWT", "Atracação", "Desatracação", ""].map((h) => (
                    <th key={h} className="px-3 py-2.5 text-left text-xs font-medium text-white/40 whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.results.map((row) => (
                  <tr key={row.id} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                    <td className="px-3 py-2 text-white/50 text-xs tabular-nums">{row.operacaomodalid}</td>
                    <td className="px-3 py-2 text-white/80 text-xs max-w-[180px] truncate">{row.navio ?? "—"}</td>
                    <td className="px-3 py-2 text-white/60 text-xs">{row.berco ?? "—"}</td>
                    <td className="px-3 py-2 text-xs">
                      {row.status ? (
                        <span className="inline-block px-2 py-0.5 rounded-full text-[10px] bg-white/8 text-white/60">
                          {row.status}
                        </span>
                      ) : "—"}
                    </td>
                    <td className="px-3 py-2 text-white/50 text-xs tabular-nums">
                      {row.dwt ? Number(row.dwt).toLocaleString("pt-BR") : "—"}
                    </td>
                    <td className="px-3 py-2 text-white/50 text-xs whitespace-nowrap">{fmtDate(row.atracacao)}</td>
                    <td className="px-3 py-2 text-white/50 text-xs whitespace-nowrap">{fmtDate(row.desatracacao)}</td>
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => openEdit(row)}
                          className="text-xs text-white/40 hover:text-white transition-colors px-2 py-1 rounded hover:bg-white/8"
                        >
                          Editar
                        </button>
                        {deleteId === row.id ? (
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => handleDelete(row.id)}
                              disabled={deleting}
                              className="text-xs text-red-400 hover:text-red-300 px-2 py-1 rounded hover:bg-red-500/10 transition-colors"
                            >
                              {deleting ? "..." : "Confirmar"}
                            </button>
                            <button
                              onClick={() => setDeleteId(null)}
                              className="text-xs text-white/30 hover:text-white px-1"
                            >
                              ✕
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => setDeleteId(row.id)}
                            className="text-xs text-white/20 hover:text-red-400 transition-colors px-2 py-1 rounded hover:bg-red-500/8"
                          >
                            Excluir
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : !loading ? (
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
              disabled={page === 1 || loading}
              className="h-8 px-3 rounded-md text-sm border border-white/10 text-white/50 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              ← Anterior
            </button>
            <span className="text-xs text-white/30">
              Página {data.page} de {data.total_pages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
              disabled={page === data.total_pages || loading}
              className="h-8 px-3 rounded-md text-sm border border-white/10 text-white/50 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              Próxima →
            </button>
          </div>
        )}
      </div>

      {/* Sheet — Create / Edit */}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent
          side="right"
          className="w-full sm:max-w-2xl bg-[#0d0e0f] border-white/8 overflow-y-auto"
        >
          <SheetHeader className="mb-6">
            <SheetTitle className="text-white text-lg font-light">
              {editing ? `Editar — ${editing.navio ?? `ID ${editing.operacaomodalid}`}` : "Nova Atracação"}
            </SheetTitle>
          </SheetHeader>

          <form onSubmit={handleSave} className="flex flex-col gap-6">
            {/* Identificação */}
            <section className="space-y-3">
              <p className="text-[11px] font-semibold text-white/30 uppercase tracking-wider">Identificação</p>
              <div className="grid grid-cols-2 gap-3">
                <FormField label="ID Operação Modal" name="operacaomodalid" type="number" value={form.operacaomodalid} onChange={handleField} required />
                <FormField label="Número Atracação" name="numero_atracacao" type="number" value={form.numero_atracacao} onChange={handleField} />
                <FormField label="Status" name="status" value={form.status} onChange={handleField} />
                <FormField label="DUV" name="duv" value={form.duv} onChange={handleField} />
                <FormField label="Escala" name="escala" value={form.escala} onChange={handleField} />
              </div>
            </section>

            {/* Navio */}
            <section className="space-y-3">
              <p className="text-[11px] font-semibold text-white/30 uppercase tracking-wider">Navio</p>
              <div className="grid grid-cols-2 gap-3">
                <div className="col-span-2">
                  <FormField label="Nome do Navio" name="navio" value={form.navio} onChange={handleField} />
                </div>
                <FormField label="IMO" name="imo" value={form.imo} onChange={handleField} />
                <FormField label="Bandeira" name="bandeira" value={form.bandeira} onChange={handleField} />
                <FormField label="DWT" name="dwt" type="number" value={form.dwt} onChange={handleField} />
                <FormField label="Comprimento (m)" name="comprimento" type="number" value={form.comprimento} onChange={handleField} />
                <FormField label="Largura (m)" name="largura" type="number" value={form.largura} onChange={handleField} />
                <FormField label="Bordo" name="bordo" value={form.bordo} onChange={handleField} />
                <FormField label="Calado Entrada (m)" name="calado_entrada" type="number" value={form.calado_entrada} onChange={handleField} />
                <FormField label="Calado Saída (m)" name="calado_saida" type="number" value={form.calado_saida} onChange={handleField} />
              </div>
            </section>

            {/* Operação */}
            <section className="space-y-3">
              <p className="text-[11px] font-semibold text-white/30 uppercase tracking-wider">Operação</p>
              <div className="grid grid-cols-2 gap-3">
                <FormField label="Berço" name="berco" value={form.berco} onChange={handleField} />
                <FormField label="Navegação" name="navegacao" value={form.navegacao} onChange={handleField} />
                <div className="col-span-2">
                  <FormField label="Agência" name="agencia" value={form.agencia} onChange={handleField} />
                </div>
                <FormField label="Procedência" name="procedencia" value={form.procedencia} onChange={handleField} />
                <FormField label="Destino" name="destino" value={form.destino} onChange={handleField} />
              </div>
            </section>

            {/* Datas */}
            <section className="space-y-3">
              <p className="text-[11px] font-semibold text-white/30 uppercase tracking-wider">Datas</p>
              <div className="grid grid-cols-2 gap-3">
                <FormField label="ETA" name="eta" type="datetime-local" value={form.eta} onChange={handleField} />
                <FormField label="ETB" name="etb" type="datetime-local" value={form.etb} onChange={handleField} />
                <FormField label="NOR" name="nor" type="datetime-local" value={form.nor} onChange={handleField} />
                <FormField label="Prontidão" name="prontidao" type="datetime-local" value={form.prontidao} onChange={handleField} />
                <FormField label="Atracação" name="atracacao" type="datetime-local" value={form.atracacao} onChange={handleField} />
                <FormField label="Início Operação" name="inicio_operacao" type="datetime-local" value={form.inicio_operacao} onChange={handleField} />
                <FormField label="Término Operação" name="termino_operacao" type="datetime-local" value={form.termino_operacao} onChange={handleField} />
                <FormField label="Desatracação" name="desatracacao" type="datetime-local" value={form.desatracacao} onChange={handleField} />
                <FormField label="ETS" name="ets" type="datetime-local" value={form.ets} onChange={handleField} />
              </div>
            </section>

            {/* Operacional */}
            <section className="space-y-3">
              <p className="text-[11px] font-semibold text-white/30 uppercase tracking-wider">Operacional</p>
              <div className="grid grid-cols-2 gap-3">
                <FormField label="Prancha (t/h)" name="prancha" type="number" value={form.prancha} onChange={handleField} />
                <FormField label="Horas Planejadas" name="horas_planejadas" type="number" value={form.horas_planejadas} onChange={handleField} />
                <FormField label="Excl. EMAP" name="excludente_emap" type="number" value={form.excludente_emap} onChange={handleField} />
                <FormField label="Excl. Intempérie" name="excludente_intemperie" type="number" value={form.excludente_intemperie} onChange={handleField} />
                <div className="col-span-2">
                  <FormField label="É Improdutividade" name="is_improdutividade" type="checkbox" value={form.is_improdutividade} onChange={handleField} />
                </div>
              </div>
            </section>

            {formError && (
              <div className="rounded-lg bg-red-500/10 border border-red-500/20 p-3 text-xs text-red-400">
                {formError}
              </div>
            )}

            <div className="flex gap-3 pt-2 pb-8">
              <Button
                type="submit"
                disabled={saving}
                className="flex-1 h-10 bg-[#0070d1] hover:bg-[#0060b8] text-white rounded-lg"
              >
                {saving ? "Salvando..." : editing ? "Salvar alterações" : "Criar atracação"}
              </Button>
              <Button
                type="button"
                onClick={() => setSheetOpen(false)}
                className="h-10 px-6 rounded-lg bg-white/5 hover:bg-white/10 text-white/70"
              >
                Cancelar
              </Button>
            </div>
          </form>
        </SheetContent>
      </Sheet>
    </div>
  )
}
