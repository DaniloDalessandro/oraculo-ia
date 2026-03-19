"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Nav from "@/components/Nav";
import { apiFetch, getToken, type UserProfile, type UserConfig } from "@/lib/api";

function Toggle({
  checked,
  onChange,
  disabled,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={() => !disabled && onChange(!checked)}
      disabled={disabled}
      className={`relative w-11 h-6 rounded-full transition-colors focus:outline-none ${
        checked ? "bg-blue-600" : "bg-[#333]"
      } ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
    >
      <span
        className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${
          checked ? "translate-x-5" : "translate-x-0"
        }`}
      />
    </button>
  );
}

function Section({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
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

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
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

export default function SettingsPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [config, setConfig] = useState<UserConfig | null>(null);
  const [nome, setNome] = useState("");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    apiFetch<UserProfile>("/settings/me").then((p) => {
      setProfile(p);
      setNome(p.nome || "");
      setConfig(p.config);
    });
  }, [router]);

  async function saveAll() {
    if (!config) return;
    setSaving(true);
    setError("");
    setSaved(false);
    try {
      await apiFetch("/settings/me", {
        method: "PUT",
        body: JSON.stringify({ nome: nome || null }),
      });
      await apiFetch("/settings/config", {
        method: "PUT",
        body: JSON.stringify(config),
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  if (!profile || !config) {
    return (
      <div className="min-h-screen bg-[#0f0f0f] flex items-center justify-center">
        <span className="w-8 h-8 border-2 border-[#333] border-t-blue-500 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0f0f0f]">
      <Nav />
      <main className="pt-14 px-6 max-w-7xl mx-auto py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-white">Configurações</h1>
            <p className="text-gray-500 text-sm mt-1">
              Personalize seu assistente e conta
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
              onClick={saveAll}
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
          {/* Perfil */}
          <Section title="Perfil">
            <Field label="E-mail">
              <p className="text-sm text-gray-500 text-right">{profile.email}</p>
            </Field>
            <Field label="Nome">
              <input
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                placeholder="Seu nome"
                className="w-full bg-[#1c1c1c] border border-[#2a2a2a] rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              />
            </Field>
            <Field label="Perfil">
              <p className="text-sm text-gray-500 text-right capitalize">{profile.perfil}</p>
            </Field>
            <Field label="WhatsApp vinculado">
              <p className="text-sm text-right font-mono text-blue-400">
                {profile.telefone_vinculado || (
                  <span className="text-gray-600">Não vinculado</span>
                )}
              </p>
            </Field>
          </Section>

          {/* Bot */}
          <Section title="Assistente" subtitle="Configurações de comportamento do bot">
            <Field label="Nome do assistente">
              <input
                value={config.nome_assistente}
                onChange={(e) => setConfig({ ...config, nome_assistente: e.target.value })}
                placeholder="Assistente"
                maxLength={100}
                className="w-full bg-[#1c1c1c] border border-[#2a2a2a] rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              />
            </Field>
            <Field label="Idioma">
              <select
                value={config.idioma}
                onChange={(e) => setConfig({ ...config, idioma: e.target.value })}
                className="w-full bg-[#1c1c1c] border border-[#2a2a2a] rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              >
                <option value="pt-BR">Português (Brasil)</option>
                <option value="en-US">English (US)</option>
                <option value="es">Español</option>
              </select>
            </Field>
            <Field label="Bot ativo">
              <div className="flex justify-end">
                <Toggle checked={config.bot_ativo} onChange={(v) => setConfig({ ...config, bot_ativo: v })} />
              </div>
            </Field>
            <Field label="Limite diário (msgs)" hint="Total de mensagens por dia">
              <input
                type="number"
                value={config.limite_diario}
                min={1}
                max={10000}
                onChange={(e) => setConfig({ ...config, limite_diario: parseInt(e.target.value) || 1 })}
                className="w-full bg-[#1c1c1c] border border-[#2a2a2a] rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              />
            </Field>
          </Section>

          {/* IA */}
          <Section
            title="Inteligência Artificial"
            subtitle="Controle o comportamento da IA"
          >
            <Field label="IA ativa" hint="Habilita respostas inteligentes">
              <div className="flex justify-end">
                <Toggle
                  checked={config.ia_ativa}
                  onChange={(v) => setConfig({ ...config, ia_ativa: v })}
                />
              </div>
            </Field>
            <Field label="Limite IA por dia" hint="Máximo de consultas com IA por dia">
              <input
                type="number"
                value={config.limite_ia_diario}
                min={1}
                max={10000}
                onChange={(e) =>
                  setConfig({ ...config, limite_ia_diario: parseInt(e.target.value) || 1 })
                }
                className="w-full bg-[#1c1c1c] border border-[#2a2a2a] rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              />
            </Field>
            <Field label="Nível de detalhe" hint="Controla o tamanho das respostas">
              <select
                value={config.nivel_detalhe}
                onChange={(e) => setConfig({ ...config, nivel_detalhe: e.target.value })}
                className="w-full bg-[#1c1c1c] border border-[#2a2a2a] rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500"
              >
                <option value="resumido">Resumido — máximo 2 linhas</option>
                <option value="normal">Normal — completo e objetivo</option>
                <option value="detalhado">Detalhado — com contexto e análise</option>
              </select>
            </Field>

            <div className="mt-2 p-3 bg-blue-500/5 border border-blue-500/20 rounded-lg">
              <p className="text-xs text-blue-400 leading-relaxed">
                💡 <strong>Como funciona:</strong> A IA converte sua pergunta em SQL,
                consulta o banco e formata a resposta em português. Veja os{" "}
                <span className="font-mono">Logs IA</span> para histórico.
              </p>
            </div>
          </Section>
        </div>
      </main>
    </div>
  );
}
