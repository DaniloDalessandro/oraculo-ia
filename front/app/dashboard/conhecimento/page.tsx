"use client"

import { useState, useEffect, useCallback } from "react"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { Separator } from "@/components/ui/separator"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

// ─── Types ────────────────────────────────────────────────────────────────────

type Choice = { value: string; label: string }

interface Meta {
  knowledge_categories: Choice[]
  knowledge_sources: Choice[]
  rule_types: Choice[]
}

interface KnowledgeItem {
  id: number
  title: string
  category: string
  category_display: string
  content: string
  source_type: string
  source_type_display: string
  source_name: string
  priority: number
  is_active: boolean
  created_at: string
  updated_at: string
}

interface GlossaryItem {
  id: number
  term: string
  definition: string
  example: string
  is_active: boolean
  created_at: string
}

interface RuleItem {
  id: number
  rule_name: string
  rule_type: string
  rule_type_display: string
  condition: string
  action: string
  priority: number
  explanation: string
  is_active: boolean
  created_at: string
}

type Tab = "knowledge" | "glossary" | "rules"

const TAB_LABELS: Record<Tab, string> = {
  knowledge: "Base de Conhecimento",
  glossary: "Glossario",
  rules: "Regras de Negocio",
}

// ─── Shared components ────────────────────────────────────────────────────────

function Badge({ active }: { active: boolean }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${active ? "bg-emerald-500/15 text-emerald-400" : "bg-white/8 text-white/40"}`}>
      {active ? "Ativo" : "Inativo"}
    </span>
  )
}

function PriorityDot({ priority }: { priority: number }) {
  const color = priority <= 3 ? "bg-red-400" : priority <= 6 ? "bg-yellow-400" : "bg-white/20"
  return <span className={`inline-block w-2 h-2 rounded-full shrink-0 mt-1.5 ${color}`} />
}

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-2xl bg-[#121314] border border-white/10 rounded-xl shadow-2xl flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/8">
          <h2 className="text-white font-semibold">{title}</h2>
          <button onClick={onClose} className="text-white/40 hover:text-white transition-colors text-xl leading-none px-2">x</button>
        </div>
        <div className="overflow-y-auto flex-1 px-6 py-5">{children}</div>
      </div>
    </div>
  )
}

function Field({ label, required, children }: { label: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label className="text-white/60 text-xs uppercase tracking-wider">
        {label}{required && <span className="text-red-400 ml-0.5">*</span>}
      </Label>
      {children}
    </div>
  )
}

const inputClass = "bg-[#0a0a0a] border-white/10 text-white placeholder:text-white/20 focus:border-[#0070d1] focus:ring-[#0070d1]/20"
const selectClass = "w-full bg-[#0a0a0a] border border-white/10 text-white rounded-md px-3 py-2 text-sm focus:outline-none focus:border-[#0070d1]"
const textareaClass = "w-full bg-[#0a0a0a] border border-white/10 text-white placeholder:text-white/20 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-[#0070d1] resize-none"

function SkeletonList() {
  return (
    <div className="space-y-2">
      {[...Array(4)].map((_, i) => <div key={i} className="h-14 rounded-lg bg-white/5 animate-pulse" />)}
    </div>
  )
}

function DeleteConfirm({ label, onCancel, onConfirm, loading }: { label: string; onCancel: () => void; onConfirm: () => void; loading: boolean }) {
  return (
    <Modal title="Confirmar exclusao" onClose={onCancel}>
      <p className="text-white/60 text-sm mb-6">
        Tem certeza que deseja excluir <span className="text-white font-medium">{label}</span>? Esta acao nao pode ser desfeita.
      </p>
      <div className="flex gap-3 justify-end">
        <Button variant="outline" onClick={onCancel} className="border-white/10 text-white/60 hover:text-white">Cancelar</Button>
        <Button onClick={onConfirm} disabled={loading} className="bg-red-600 hover:bg-red-700 text-white">
          {loading ? "Excluindo..." : "Excluir"}
        </Button>
      </div>
    </Modal>
  )
}

function FormActions({ onCancel, onSave, saving, disabled }: { onCancel: () => void; onSave: () => void; saving: boolean; disabled: boolean }) {
  return (
    <div className="flex gap-3 justify-end pt-2">
      <Button variant="outline" onClick={onCancel} className="border-white/10 text-white/60 hover:text-white">Cancelar</Button>
      <Button onClick={onSave} disabled={saving || disabled} className="bg-[#0070d1] hover:bg-[#0060b8] text-white">
        {saving ? "Salvando..." : "Salvar"}
      </Button>
    </div>
  )
}

// ─── Knowledge Tab ────────────────────────────────────────────────────────────

function KnowledgeTab({ meta }: { meta: Meta }) {
  const [items, setItems] = useState<KnowledgeItem[]>([])
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState<KnowledgeItem | null>(null)
  const [creating, setCreating] = useState(false)
  const [deleting, setDeleting] = useState<KnowledgeItem | null>(null)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState<Partial<KnowledgeItem>>({})

  const load = useCallback(async () => {
    setLoading(true)
    const r = await fetch("/api/knowledge")
    setItems(await r.json())
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  function openCreate() {
    setForm({ priority: 5, is_active: true, source_type: "manual", category: meta.knowledge_categories[0]?.value })
    setCreating(true)
  }

  function openEdit(item: KnowledgeItem) { setForm({ ...item }); setEditing(item) }
  function closeForm() { setEditing(null); setCreating(false) }

  async function save() {
    setSaving(true)
    const isEdit = !!editing
    await fetch(isEdit ? `/api/knowledge/${editing!.id}` : "/api/knowledge", {
      method: isEdit ? "PATCH" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    })
    setSaving(false); closeForm(); load()
  }

  async function doDelete() {
    if (!deleting) return
    setSaving(true)
    await fetch(`/api/knowledge/${deleting.id}`, { method: "DELETE" })
    setSaving(false); setDeleting(null); load()
  }

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <p className="text-white/40 text-sm">{items.length} registros</p>
        <Button onClick={openCreate} className="bg-[#0070d1] hover:bg-[#0060b8] text-white h-9 px-4 text-sm">+ Novo</Button>
      </div>
      {loading ? <SkeletonList /> : (
        <div className="space-y-2">
          {items.map((item) => (
            <div key={item.id} className="flex items-start gap-3 rounded-lg bg-[#121314] border border-white/8 px-4 py-3 hover:border-white/15 transition-colors">
              <PriorityDot priority={item.priority} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-white text-sm font-medium">{item.title}</span>
                  <span className="text-[11px] text-white/30 bg-white/5 px-2 py-0.5 rounded-full">{item.category_display}</span>
                  <Badge active={item.is_active} />
                </div>
                <p className="text-white/40 text-xs mt-1 line-clamp-2">{item.content}</p>
              </div>
              <div className="flex gap-2 shrink-0">
                <button onClick={() => openEdit(item)} className="text-white/30 hover:text-white text-xs px-2 py-1 rounded hover:bg-white/5 transition-colors">Editar</button>
                <button onClick={() => setDeleting(item)} className="text-red-400/50 hover:text-red-400 text-xs px-2 py-1 rounded hover:bg-red-400/5 transition-colors">Excluir</button>
              </div>
            </div>
          ))}
          {items.length === 0 && <p className="text-center text-white/20 py-12 text-sm">Nenhum registro cadastrado.</p>}
        </div>
      )}

      {(creating || !!editing) && (
        <Modal title={editing ? "Editar conhecimento" : "Novo conhecimento"} onClose={closeForm}>
          <div className="space-y-4">
            <Field label="Titulo" required>
              <Input className={inputClass} value={form.title ?? ""} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="Ex: Regra de prioridade berco 101" />
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Categoria" required>
                <select className={selectClass} value={form.category ?? ""} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                  {meta.knowledge_categories.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                </select>
              </Field>
              <Field label="Prioridade (1=alta, 10=baixa)">
                <Input className={inputClass} type="number" min={1} max={10} value={form.priority ?? 5} onChange={(e) => setForm({ ...form, priority: Number(e.target.value) })} />
              </Field>
            </div>
            <Field label="Conteudo" required>
              <textarea className={textareaClass} rows={5} value={form.content ?? ""} onChange={(e) => setForm({ ...form, content: e.target.value })} placeholder="Descreva o conhecimento, regra ou contexto..." />
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Origem">
                <select className={selectClass} value={form.source_type ?? "manual"} onChange={(e) => setForm({ ...form, source_type: e.target.value })}>
                  {meta.knowledge_sources.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                </select>
              </Field>
              <Field label="Nome da Fonte">
                <Input className={inputClass} value={form.source_name ?? ""} onChange={(e) => setForm({ ...form, source_name: e.target.value })} placeholder="Ex: Manual Operacional 2024" />
              </Field>
            </div>
            <div className="flex items-center gap-2">
              <input type="checkbox" id="kb-active" checked={form.is_active ?? true} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} className="accent-[#0070d1]" />
              <label htmlFor="kb-active" className="text-white/60 text-sm">Ativo</label>
            </div>
            <FormActions onCancel={closeForm} onSave={save} saving={saving} disabled={!form.title || !form.content} />
          </div>
        </Modal>
      )}

      {deleting && <DeleteConfirm label={deleting.title} onCancel={() => setDeleting(null)} onConfirm={doDelete} loading={saving} />}
    </>
  )
}

// ─── Glossary Tab ─────────────────────────────────────────────────────────────

function GlossaryTab() {
  const [items, setItems] = useState<GlossaryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState<GlossaryItem | null>(null)
  const [creating, setCreating] = useState(false)
  const [deleting, setDeleting] = useState<GlossaryItem | null>(null)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState<Partial<GlossaryItem>>({})

  const load = useCallback(async () => {
    setLoading(true)
    const r = await fetch("/api/glossary")
    setItems(await r.json())
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  function openCreate() { setForm({ is_active: true }); setCreating(true) }
  function openEdit(item: GlossaryItem) { setForm({ ...item }); setEditing(item) }
  function closeForm() { setEditing(null); setCreating(false) }

  async function save() {
    setSaving(true)
    const isEdit = !!editing
    await fetch(isEdit ? `/api/glossary/${editing!.id}` : "/api/glossary", {
      method: isEdit ? "PATCH" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    })
    setSaving(false); closeForm(); load()
  }

  async function doDelete() {
    if (!deleting) return
    setSaving(true)
    await fetch(`/api/glossary/${deleting.id}`, { method: "DELETE" })
    setSaving(false); setDeleting(null); load()
  }

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <p className="text-white/40 text-sm">{items.length} termos</p>
        <Button onClick={openCreate} className="bg-[#0070d1] hover:bg-[#0060b8] text-white h-9 px-4 text-sm">+ Novo</Button>
      </div>
      {loading ? <SkeletonList /> : (
        <div className="space-y-2">
          {items.map((item) => (
            <div key={item.id} className="flex items-start gap-4 rounded-lg bg-[#121314] border border-white/8 px-4 py-3 hover:border-white/15 transition-colors">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-white text-sm font-semibold">{item.term}</span>
                  <Badge active={item.is_active} />
                </div>
                <p className="text-white/40 text-xs mt-1 line-clamp-2">{item.definition}</p>
                {item.example && <p className="text-white/25 text-xs mt-0.5 italic line-clamp-1">Ex: {item.example}</p>}
              </div>
              <div className="flex gap-2 shrink-0">
                <button onClick={() => openEdit(item)} className="text-white/30 hover:text-white text-xs px-2 py-1 rounded hover:bg-white/5 transition-colors">Editar</button>
                <button onClick={() => setDeleting(item)} className="text-red-400/50 hover:text-red-400 text-xs px-2 py-1 rounded hover:bg-red-400/5 transition-colors">Excluir</button>
              </div>
            </div>
          ))}
          {items.length === 0 && <p className="text-center text-white/20 py-12 text-sm">Nenhum termo cadastrado.</p>}
        </div>
      )}

      {(creating || !!editing) && (
        <Modal title={editing ? "Editar termo" : "Novo termo"} onClose={closeForm}>
          <div className="space-y-4">
            <Field label="Termo" required>
              <Input className={inputClass} value={form.term ?? ""} onChange={(e) => setForm({ ...form, term: e.target.value })} placeholder="Ex: PLR, Berco, Atracacao..." />
            </Field>
            <Field label="Definicao" required>
              <textarea className={textareaClass} rows={4} value={form.definition ?? ""} onChange={(e) => setForm({ ...form, definition: e.target.value })} placeholder="Definicao tecnica do termo..." />
            </Field>
            <Field label="Exemplo de uso">
              <textarea className={textareaClass} rows={2} value={form.example ?? ""} onChange={(e) => setForm({ ...form, example: e.target.value })} placeholder="Ex: O PLR do berco 101 foi de 1200 t/h..." />
            </Field>
            <div className="flex items-center gap-2">
              <input type="checkbox" id="gl-active" checked={form.is_active ?? true} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} className="accent-[#0070d1]" />
              <label htmlFor="gl-active" className="text-white/60 text-sm">Ativo</label>
            </div>
            <FormActions onCancel={closeForm} onSave={save} saving={saving} disabled={!form.term || !form.definition} />
          </div>
        </Modal>
      )}

      {deleting && <DeleteConfirm label={deleting.term} onCancel={() => setDeleting(null)} onConfirm={doDelete} loading={saving} />}
    </>
  )
}

// ─── Rules Tab ────────────────────────────────────────────────────────────────

function RulesTab({ meta }: { meta: Meta }) {
  const [items, setItems] = useState<RuleItem[]>([])
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState<RuleItem | null>(null)
  const [creating, setCreating] = useState(false)
  const [deleting, setDeleting] = useState<RuleItem | null>(null)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState<Partial<RuleItem>>({})

  const load = useCallback(async () => {
    setLoading(true)
    const r = await fetch("/api/rules")
    setItems(await r.json())
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  function openCreate() { setForm({ priority: 5, is_active: true, rule_type: meta.rule_types[0]?.value }); setCreating(true) }
  function openEdit(item: RuleItem) { setForm({ ...item }); setEditing(item) }
  function closeForm() { setEditing(null); setCreating(false) }

  async function save() {
    setSaving(true)
    const isEdit = !!editing
    await fetch(isEdit ? `/api/rules/${editing!.id}` : "/api/rules", {
      method: isEdit ? "PATCH" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    })
    setSaving(false); closeForm(); load()
  }

  async function doDelete() {
    if (!deleting) return
    setSaving(true)
    await fetch(`/api/rules/${deleting.id}`, { method: "DELETE" })
    setSaving(false); setDeleting(null); load()
  }

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <p className="text-white/40 text-sm">{items.length} regras</p>
        <Button onClick={openCreate} className="bg-[#0070d1] hover:bg-[#0060b8] text-white h-9 px-4 text-sm">+ Nova</Button>
      </div>
      {loading ? <SkeletonList /> : (
        <div className="space-y-2">
          {items.map((item) => (
            <div key={item.id} className="flex items-start gap-3 rounded-lg bg-[#121314] border border-white/8 px-4 py-3 hover:border-white/15 transition-colors">
              <PriorityDot priority={item.priority} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-white text-sm font-medium">{item.rule_name}</span>
                  <span className="text-[11px] text-white/30 bg-white/5 px-2 py-0.5 rounded-full">{item.rule_type_display}</span>
                  <Badge active={item.is_active} />
                </div>
                <p className="text-white/40 text-xs mt-1 line-clamp-1"><span className="text-white/25">Condicao:</span> {item.condition}</p>
                <p className="text-white/40 text-xs line-clamp-1"><span className="text-white/25">Acao:</span> {item.action}</p>
              </div>
              <div className="flex gap-2 shrink-0">
                <button onClick={() => openEdit(item)} className="text-white/30 hover:text-white text-xs px-2 py-1 rounded hover:bg-white/5 transition-colors">Editar</button>
                <button onClick={() => setDeleting(item)} className="text-red-400/50 hover:text-red-400 text-xs px-2 py-1 rounded hover:bg-red-400/5 transition-colors">Excluir</button>
              </div>
            </div>
          ))}
          {items.length === 0 && <p className="text-center text-white/20 py-12 text-sm">Nenhuma regra cadastrada.</p>}
        </div>
      )}

      {(creating || !!editing) && (
        <Modal title={editing ? "Editar regra" : "Nova regra de negocio"} onClose={closeForm}>
          <div className="space-y-4">
            <Field label="Nome da Regra" required>
              <Input className={inputClass} value={form.rule_name ?? ""} onChange={(e) => setForm({ ...form, rule_name: e.target.value })} placeholder="Ex: Prioridade navios tanque berco 101" />
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Tipo" required>
                <select className={selectClass} value={form.rule_type ?? ""} onChange={(e) => setForm({ ...form, rule_type: e.target.value })}>
                  {meta.rule_types.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                </select>
              </Field>
              <Field label="Prioridade (1=alta, 10=baixa)">
                <Input className={inputClass} type="number" min={1} max={10} value={form.priority ?? 5} onChange={(e) => setForm({ ...form, priority: Number(e.target.value) })} />
              </Field>
            </div>
            <Field label="Condicao (quando aplicar)" required>
              <textarea className={textareaClass} rows={3} value={form.condition ?? ""} onChange={(e) => setForm({ ...form, condition: e.target.value })} placeholder="Quando o navio e do tipo tanque..." />
            </Field>
            <Field label="Acao (o que fazer)" required>
              <textarea className={textareaClass} rows={3} value={form.action ?? ""} onChange={(e) => setForm({ ...form, action: e.target.value })} placeholder="Direcionar preferencialmente para o berco 101..." />
            </Field>
            <Field label="Explicacao adicional">
              <textarea className={textareaClass} rows={2} value={form.explanation ?? ""} onChange={(e) => setForm({ ...form, explanation: e.target.value })} placeholder="Contexto ou justificativa adicional..." />
            </Field>
            <div className="flex items-center gap-2">
              <input type="checkbox" id="rl-active" checked={form.is_active ?? true} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} className="accent-[#0070d1]" />
              <label htmlFor="rl-active" className="text-white/60 text-sm">Ativa</label>
            </div>
            <FormActions onCancel={closeForm} onSave={save} saving={saving} disabled={!form.rule_name || !form.condition || !form.action} />
          </div>
        </Modal>
      )}

      {deleting && <DeleteConfirm label={deleting.rule_name} onCancel={() => setDeleting(null)} onConfirm={doDelete} loading={saving} />}
    </>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function ConhecimentoPage() {
  const [tab, setTab] = useState<Tab>("knowledge")
  const [meta, setMeta] = useState<Meta | null>(null)

  useEffect(() => {
    fetch("/api/knowledge/meta").then((r) => r.json()).then(setMeta)
  }, [])

  return (
    <div className="flex flex-col h-full min-h-svh">
      <header className="flex h-14 shrink-0 items-center gap-3 px-4 border-b border-white/8">
        <SidebarTrigger className="text-white/50 hover:text-white transition-colors" />
        <Separator orientation="vertical" className="h-4 bg-white/10 data-vertical:h-4 data-vertical:self-auto" />
        <span className="text-sm font-medium text-white/60">Base de Conhecimento</span>
      </header>

      <div className="flex-1 p-6 space-y-6">
        <div className="space-y-1">
          <h1 className="text-white" style={{ fontSize: "35px", fontWeight: 300 }}>
            Base de Conhecimento
          </h1>
          <p className="text-white/40 text-sm">Gerencie as informacoes que o agente ITA usa para responder.</p>
        </div>

        <div className="flex gap-1 bg-[#121314] border border-white/8 rounded-lg p-1 w-fit">
          {(Object.keys(TAB_LABELS) as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
                tab === t ? "bg-[#0070d1] text-white" : "text-white/40 hover:text-white hover:bg-white/5"
              }`}
            >
              {TAB_LABELS[t]}
            </button>
          ))}
        </div>

        <div>
          {!meta ? <SkeletonList /> : (
            <>
              {tab === "knowledge" && <KnowledgeTab meta={meta} />}
              {tab === "glossary" && <GlossaryTab />}
              {tab === "rules" && <RulesTab meta={meta} />}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
