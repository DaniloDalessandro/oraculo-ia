"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Nav from "@/components/Nav";
import { apiFetch, getToken, type SystemSettings } from "@/lib/api";

function Toggle({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`relative w-11 h-6 rounded-full transition-colors focus:outline-none cursor-pointer ${
        checked ? "bg-blue-600" : "bg-[#333]"
      }`}
    >
      <span
        className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${
          checked ? "translate-x-5" : "translate-x-0"
        }`}
      />
    </button>
  );
}

function Section({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-[#141414] border border-[#222] rounded-xl overflow-hidden">
      <div className="px-6 py-4 border-b border-[#222]">
        <h2 className="text-sm font-semibold text-white">{title}</h2>
        {subtitle && <p className="text-xs text-gray-600 mt-0.5">{subtitle}</p>}
      </div>
      <div className="px-6 py-5 space-y-5">{children}</div>
    </div>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div>
        <label className="text-sm text-gray-400">{label}</label>
        {hint && <p className="text-xs text-gray-600 mt-0.5">{hint}</p>}
      </div>
      <div className="w-56 shrink-0">{children}</div>
    </div>
  );
}

function NumberInput({
  value,
  onChange,
  min,
  max,
  step,
}: {
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  step?: number;
}) {
  return (
    <input
      type="number"
      value={value}
      min={min}
      max={max}
      step={step}
      onChange={(e) => onChange(Number(e.target.value))}
      className="w-full bg-[#1c1c1c] border border-[#2a2a2a] rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
    />
  );
}

function TextInput({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full bg-[#1c1c1c] border border-[#2a2a2a] rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
    />
  );
}

export default function SistemaPage() {
  const router = useRouter();
  const [s, setS] = useState<SystemSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    apiFetch<SystemSettings>("/admin/system-settings").then(setS).catch((e) => {
      setError((e as Error).message);
    });
  }, [router]);

  function set<K extends keyof SystemSettings>(key: K, value: SystemSettings[K]) {
    setS((prev) => prev ? { ...prev, [key]: value } : prev);
  }

  async function save() {
    if (!s) return;
    setSaving(true);
    setError("");
    setSaved(false);
    try {
      const updated = await apiFetch<SystemSettings>("/admin/system-settings", {
        method: "PUT",
        body: JSON.stringify(s),
      });
      setS(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  if (!s) {
    return (
      <div className="min-h-screen bg-[#0f0f0f] flex items-center justify-center">
        {error ? (
          <p className="text-red-400 text-sm">{error}</p>
        ) : (
          <span className="w-8 h-8 border-2 border-[#333] border-t-blue-500 rounded-full animate-spin" />
        )}
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0f0f0f]">
      <Nav />
      <main className="pt-14 px-6 max-w-7xl mx-auto py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-white">Configurações do Sistema</h1>
            <p className="text-gray-500 text-sm mt-1">
              Parâmetros globais da plataforma — apenas administradores
            </p>
          </div>
          <div className="flex items-center gap-3">
            {saved && (
              <span className="text-green-400 text-sm">✓ Salvo com sucesso</span>
            )}
            {error && (
              <span className="text-red-400 text-sm">{error}</span>
            )}
            <button
              onClick={save}
              disabled={saving}
              className="bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 disabled:cursor-not-allowed text-white font-semibold px-6 py-2.5 rounded-xl text-sm transition-colors flex items-center gap-2"
            >
              {saving ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Salvando...
                </>
              ) : (
                "Salvar configurações"
              )}
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* IA — Provider e modelos */}
          <Section title="Provedor de IA" subtitle="Qual API de linguagem o sistema usa">
            <Field label="Provedor ativo">
              <select
                value={s.ai_provider}
                onChange={(e) => set("ai_provider", e.target.value)}
                className="w-full bg-[#1c1c1c] border border-[#2a2a2a] rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              >
                <option value="groq">Groq (llama)</option>
                <option value="gemini">Google Gemini</option>
                <option value="openai">OpenAI (GPT)</option>
              </select>
            </Field>
            <Field label="Modelo Groq" hint="Ex: llama-3.3-70b-versatile">
              <TextInput
                value={s.groq_model}
                onChange={(v) => set("groq_model", v)}
                placeholder="llama-3.3-70b-versatile"
              />
            </Field>
            <Field label="Modelo Gemini" hint="Ex: gemini-2.0-flash">
              <TextInput
                value={s.gemini_model}
                onChange={(v) => set("gemini_model", v)}
                placeholder="gemini-2.0-flash"
              />
            </Field>
            <Field label="Modelo OpenAI" hint="Ex: gpt-4o-mini">
              <TextInput
                value={s.openai_model}
                onChange={(v) => set("openai_model", v)}
                placeholder="gpt-4o-mini"
              />
            </Field>
          </Section>

          {/* IA — Comportamento */}
          <Section title="Comportamento da IA" subtitle="Parâmetros de geração de texto">
            <Field label="Max tokens" hint="Limite de tokens por resposta (100–32000)">
              <NumberInput
                value={s.ai_max_tokens}
                onChange={(v) => set("ai_max_tokens", v)}
                min={100}
                max={32000}
              />
            </Field>
            <Field label="Temperature" hint="Criatividade: 0 = focado, 1 = criativo">
              <NumberInput
                value={s.ai_temperature}
                onChange={(v) => set("ai_temperature", v)}
                min={0}
                max={2}
                step={0.1}
              />
            </Field>
            <Field label="Tamanho do contexto" hint="Nº de mensagens anteriores enviadas à IA">
              <NumberInput
                value={s.ai_context_size}
                onChange={(v) => set("ai_context_size", v)}
                min={1}
                max={50}
              />
            </Field>
            <Field label="Limite de linhas SQL" hint="Máx. de linhas retornadas por query">
              <NumberInput
                value={s.ai_sql_row_limit}
                onChange={(v) => set("ai_sql_row_limit", v)}
                min={1}
                max={1000}
              />
            </Field>
            <Field label="Timeout da IA (s)" hint="Segundos antes de cancelar a chamada">
              <NumberInput
                value={s.ai_timeout_seconds}
                onChange={(v) => set("ai_timeout_seconds", v)}
                min={5}
                max={120}
              />
            </Field>
          </Section>

          {/* Cache */}
          <Section title="Cache de respostas" subtitle="Evita chamadas repetidas à API de IA">
            <Field label="Cache ativo">
              <div className="flex justify-end">
                <Toggle
                  checked={s.ai_cache_enabled}
                  onChange={(v) => set("ai_cache_enabled", v)}
                />
              </div>
            </Field>
            <Field label="TTL do cache (s)" hint="Tempo de vida de cada resposta cacheada">
              <NumberInput
                value={s.ai_cache_ttl_seconds}
                onChange={(v) => set("ai_cache_ttl_seconds", v)}
                min={60}
                max={86400}
              />
            </Field>
          </Section>

          {/* Rate limiting */}
          <Section title="Rate Limiting" subtitle="Controle de uso por usuário no WhatsApp">
            <Field label="Mensagens por minuto" hint="Limite por usuário do WhatsApp">
              <NumberInput
                value={s.rate_limit_per_minute}
                onChange={(v) => set("rate_limit_per_minute", v)}
                min={1}
                max={100}
              />
            </Field>
            <Field label="Burst extra" hint="Tolerância adicional acima do limite">
              <NumberInput
                value={s.rate_limit_burst}
                onChange={(v) => set("rate_limit_burst", v)}
                min={0}
                max={50}
              />
            </Field>
          </Section>

          {/* WhatsApp / Sessão */}
          <Section title="Sessão WhatsApp" subtitle="Controle de expiração de sessões">
            <Field label="Expirar sessão após (h)" hint="Sessões inativas são encerradas">
              <NumberInput
                value={s.whatsapp_session_expire_hours}
                onChange={(v) => set("whatsapp_session_expire_hours", v)}
                min={1}
                max={168}
              />
            </Field>
          </Section>

          {/* Segurança de login */}
          <Section title="Segurança de login" subtitle="Proteção contra ataques de força bruta">
            <Field label="Tentativas antes de bloquear">
              <NumberInput
                value={s.login_max_attempts}
                onChange={(v) => set("login_max_attempts", v)}
                min={1}
                max={20}
              />
            </Field>
            <Field label="Bloqueio por (s)" hint="Duração do bloqueio após tentativas excedidas">
              <NumberInput
                value={s.login_lockout_seconds}
                onChange={(v) => set("login_lockout_seconds", v)}
                min={60}
                max={86400}
              />
            </Field>
          </Section>

        </div>

        <p className="mt-6 text-xs text-gray-700 text-center">
          As alterações entram em vigor imediatamente e persistem após reinicialização do servidor.
          Credenciais de API (chaves secretas) devem ser configuradas via variáveis de ambiente.
        </p>
      </main>
    </div>
  );
}
