"use client"

import { useRef, useState, useTransition } from "react"
import { Loader2, Copy, Check, ChevronDown, ChevronUp, ThumbsUp, ThumbsDown, ArrowUp } from "lucide-react"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { Separator } from "@/components/ui/separator"
import { ChatChartRenderer } from "@/components/chat/ChatChartRenderer"
import type { ChatMessage, AgentResponse } from "@/components/chat/types"

const EXAMPLE_QUESTIONS = [
  "Quantas atracações ocorreram em 2025?",
  "Gere um gráfico do total de PLR por mês em 2025",
  "Qual berço teve mais operações?",
  "Compare gasolina em 2024 e 2025",
  "Mostre a evolução mensal de tonelagem",
  "Liste os 10 maiores navios por DWT",
]

export default function ITAPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [isPending, startTransition] = useTransition()
  const bottomRef = useRef<HTMLDivElement>(null)

  const handleFeedback = async (msgId: string, accepted: boolean) => {
    const msg = messages.find((m) => m.id === msgId)
    if (!msg || msg.feedback) return
    setMessages((prev) =>
      prev.map((m) => (m.id === msgId ? { ...m, feedback: accepted ? "up" : "down" } : m))
    )
    try {
      await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: msg.question ?? msg.text,
          generated_sql: msg.sql ?? "",
          accepted,
        }),
      })
    } catch {}
  }

  const scrollToBottom = () =>
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50)

  const sendMessage = (question: string) => {
    const q = question.trim()
    if (!q || isPending) return

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      text: q,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMsg])
    setInput("")
    scrollToBottom()

    startTransition(async () => {
      try {
        const history = messages.slice(-20).map((m) => ({ role: m.role, text: m.text }))
        const res = await fetch("/api/agent", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: q, conversation_history: history }),
        })
        const data: AgentResponse = await res.json()
        const assistantMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: "assistant",
          text: data.answer ?? "Sem resposta.",
          question: q,
          chart: data.chart?.should_render ? data.chart : null,
          sql: data.sql,
          intent: data.intent,
          status: data.status,
          executionMs: data.filters?.execution_time_ms,
          timestamp: new Date(),
        }
        setMessages((prev) => [...prev, assistantMsg])
        scrollToBottom()
      } catch {
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            text: "Erro ao conectar com o servidor. Tente novamente.",
            status: "error",
            timestamp: new Date(),
          },
        ])
        scrollToBottom()
      }
    })
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  return (
    <div className="flex flex-col h-svh">
      {/* Top bar */}
      <header className="flex h-14 shrink-0 items-center gap-3 px-4 border-b border-white/8 bg-[#0a0a0a]">
        <SidebarTrigger className="text-white/50 hover:text-white transition-colors" />
        <Separator
          orientation="vertical"
          className="h-4 bg-white/10 data-vertical:h-4 data-vertical:self-auto"
        />
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded-full bg-[#0070d1] flex items-center justify-center">
            <svg width="9" height="9" viewBox="0 0 9 9" fill="none">
              <circle cx="4.5" cy="4.5" r="3.5" stroke="white" strokeWidth="1.2" />
              <circle cx="4.5" cy="4.5" r="1.2" fill="white" />
            </svg>
          </div>
          <span className="text-sm font-medium text-white/70">ITA</span>
          <span className="text-[10px] text-white/25 px-1.5 py-0.5 rounded-full border border-white/10 font-medium">
            IA
          </span>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
        {messages.length === 0 && <EmptyState onExample={sendMessage} />}
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} onFeedback={handleFeedback} />
        ))}
        {isPending && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="shrink-0 px-4 pb-4 pt-3 bg-[#0a0a0a] border-t border-white/8">
        <div className="max-w-3xl mx-auto">
          <div className="relative flex items-end gap-2 rounded-xl bg-[#181818] border border-white/10 px-4 py-3 focus-within:border-[#0070d1]/50 transition-colors">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Pergunte sobre atracações, cargas, berços..."
              disabled={isPending}
              rows={1}
              className="flex-1 bg-transparent text-white text-sm placeholder:text-white/25 resize-none focus:outline-none leading-relaxed max-h-32 overflow-auto"
              style={{ minHeight: "24px" }}
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={isPending || !input.trim()}
              className="shrink-0 w-8 h-8 rounded-full bg-[#0070d1] hover:bg-[#0064b7] disabled:bg-white/8 disabled:cursor-not-allowed flex items-center justify-center transition-colors"
            >
              {isPending ? (
                <Loader2 className="w-3.5 h-3.5 text-white animate-spin" />
              ) : (
                <ArrowUp className="w-3.5 h-3.5 text-white" />
              )}
            </button>
          </div>
          <p className="text-center text-[11px] text-white/20 mt-2">
            Enter para enviar · Shift+Enter para nova linha
          </p>
        </div>
      </div>
    </div>
  )
}

// ─── Sub-components ───────────────────────────────────────────────────────── //

function EmptyState({ onExample }: { onExample: (q: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full min-h-[50vh] gap-8 text-center max-w-2xl mx-auto">
      <div className="space-y-4">
        <div className="w-16 h-16 rounded-2xl bg-[#0070d1]/10 border border-[#0070d1]/20 flex items-center justify-center mx-auto">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="9" stroke="#0070d1" strokeWidth="1.5" />
            <circle cx="12" cy="12" r="3" fill="#0070d1" />
          </svg>
        </div>
        <div className="space-y-1.5">
          <h2 className="text-white font-semibold text-xl">ITA</h2>
          <p className="text-white/40 text-sm leading-relaxed max-w-sm mx-auto">
            Inteligência de dados portuários. Pergunte sobre operações, cargas, berços e navios em linguagem natural.
          </p>
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full">
        {EXAMPLE_QUESTIONS.map((q) => (
          <button
            key={q}
            onClick={() => onExample(q)}
            className="text-left text-sm px-4 py-3 rounded-lg bg-[#121314] border border-white/8 hover:border-[#0070d1]/40 hover:bg-[#0070d1]/5 text-white/50 hover:text-white/80 transition-all"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  )
}

function MessageBubble({
  message,
  onFeedback,
}: {
  message: ChatMessage
  onFeedback: (id: string, accepted: boolean) => void
}) {
  const isUser = message.role === "user"

  return (
    <div className={`flex gap-3 max-w-3xl mx-auto ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div className="shrink-0 w-7 h-7 rounded-full bg-[#0070d1]/15 border border-[#0070d1]/20 flex items-center justify-center mt-0.5">
          <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
            <circle cx="5.5" cy="5.5" r="4" stroke="#0070d1" strokeWidth="1.2" />
            <circle cx="5.5" cy="5.5" r="1.4" fill="#0070d1" />
          </svg>
        </div>
      )}

      <div className={`flex flex-col gap-2 ${isUser ? "items-end" : "items-start"} max-w-[85%]`}>
        <div
          className={`px-4 py-3 text-sm leading-relaxed ${
            isUser
              ? "bg-[#0070d1] text-white rounded-2xl rounded-br-sm"
              : message.status === "clarifying"
              ? "bg-[#121314] text-white/85 rounded-2xl rounded-bl-sm border border-[#0070d1]/20"
              : "bg-[#121314] text-white/85 rounded-2xl rounded-bl-sm"
          }`}
        >
          <pre className="whitespace-pre-wrap font-sans">{message.text}</pre>
        </div>

        {message.chart?.should_render && (
          <div className="w-full max-w-2xl">
            <ChatChartRenderer config={message.chart} />
          </div>
        )}

        {!isUser && message.status !== "clarifying" && (
          <div className="flex items-center justify-between w-full gap-2">
            {message.sql || message.executionMs ? (
              <MessageMeta sql={message.sql} executionMs={message.executionMs} intent={message.intent} />
            ) : (
              <span />
            )}
            <FeedbackButtons
              feedback={message.feedback}
              onUp={() => onFeedback(message.id, true)}
              onDown={() => onFeedback(message.id, false)}
            />
          </div>
        )}
      </div>

      {isUser && (
        <div className="shrink-0 w-7 h-7 rounded-full bg-white/8 flex items-center justify-center mt-0.5">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <circle cx="6" cy="3.5" r="2.5" stroke="rgba(255,255,255,0.45)" strokeWidth="1.2" />
            <path d="M1 11c0-2.76 2.24-5 5-5s5 2.24 5 5" stroke="rgba(255,255,255,0.45)" strokeWidth="1.2" strokeLinecap="round" />
          </svg>
        </div>
      )}
    </div>
  )
}

function MessageMeta({
  sql,
  executionMs,
  intent,
}: {
  sql?: string
  executionMs?: number
  intent?: string
}) {
  const [expanded, setExpanded] = useState(false)
  const [copied, setCopied] = useState(false)

  const copySQL = () => {
    if (sql) {
      navigator.clipboard.writeText(sql)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    }
  }

  return (
    <div className="w-full space-y-1.5">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center gap-1.5 text-[11px] text-white/25 hover:text-white/50 transition-colors"
      >
        {expanded ? <ChevronUp className="size-3" /> : <ChevronDown className="size-3" />}
        {intent && <span className="capitalize">{intent.replace(/_/g, " ")}</span>}
        {executionMs != null && <span className="tabular-nums">· {executionMs}ms</span>}
      </button>

      {expanded && sql && (
        <div className="relative">
          <pre className="text-[11px] bg-black/50 border border-white/8 rounded-lg p-3 overflow-x-auto text-white/35 font-mono max-h-40">
            {sql}
          </pre>
          <button
            onClick={copySQL}
            className="absolute top-2 right-2 p-1 rounded hover:bg-white/8 transition-colors"
            title="Copiar SQL"
          >
            {copied ? (
              <Check className="size-3.5 text-emerald-400" />
            ) : (
              <Copy className="size-3.5 text-white/30" />
            )}
          </button>
        </div>
      )}
    </div>
  )
}

function FeedbackButtons({
  feedback,
  onUp,
  onDown,
}: {
  feedback?: "up" | "down"
  onUp: () => void
  onDown: () => void
}) {
  const done = !!feedback
  return (
    <div className="flex items-center gap-0.5 shrink-0">
      <button
        onClick={onUp}
        disabled={done}
        title="Boa resposta"
        className={`p-1.5 rounded-full transition-colors ${
          feedback === "up"
            ? "text-emerald-400"
            : "text-white/20 hover:text-emerald-400 hover:bg-emerald-400/10 disabled:cursor-default"
        }`}
      >
        <ThumbsUp className="size-3" />
      </button>
      <button
        onClick={onDown}
        disabled={done}
        title="Resposta ruim"
        className={`p-1.5 rounded-full transition-colors ${
          feedback === "down"
            ? "text-red-400"
            : "text-white/20 hover:text-red-400 hover:bg-red-400/10 disabled:cursor-default"
        }`}
      >
        <ThumbsDown className="size-3" />
      </button>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="flex gap-3 max-w-3xl mx-auto">
      <div className="shrink-0 w-7 h-7 rounded-full bg-[#0070d1]/15 border border-[#0070d1]/20 flex items-center justify-center">
        <svg width="11" height="11" viewBox="0 0 11 11" fill="none">
          <circle cx="5.5" cy="5.5" r="4" stroke="#0070d1" strokeWidth="1.2" />
          <circle cx="5.5" cy="5.5" r="1.4" fill="#0070d1" />
        </svg>
      </div>
      <div className="bg-[#121314] rounded-2xl rounded-bl-sm px-4 py-3.5 flex gap-1.5 items-center">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="w-1.5 h-1.5 rounded-full bg-white/25 animate-bounce"
            style={{ animationDelay: `${i * 0.15}s` }}
          />
        ))}
      </div>
    </div>
  )
}
