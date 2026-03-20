"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Nav from "@/components/Nav";
import { apiFetch, getToken, type UserProfile } from "@/lib/api";

interface ApiError {
  detail?: string;
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
      <div className="px-6 py-5 space-y-4">{children}</div>
    </div>
  );
}

function InputField({
  label,
  value,
  onChange,
  type = "text",
  placeholder,
  readOnly,
  hint,
}: {
  label: string;
  value: string;
  onChange?: (v: string) => void;
  type?: string;
  placeholder?: string;
  readOnly?: boolean;
  hint?: string;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm text-gray-400 font-medium">{label}</label>
      {hint && <p className="text-xs text-gray-600">{hint}</p>}
      <input
        type={type}
        value={value}
        onChange={onChange ? (e) => onChange(e.target.value) : undefined}
        placeholder={placeholder}
        readOnly={readOnly}
        className={`w-full bg-[#1c1c1c] border rounded-lg px-3 py-2 text-sm focus:outline-none transition ${
          readOnly
            ? "border-[#222] text-gray-600 cursor-default"
            : "border-[#2a2a2a] text-white focus:border-blue-500"
        }`}
      />
    </div>
  );
}

export default function PerfilPage() {
  const router = useRouter();
  const [profile, setProfile] = useState<UserProfile | null>(null);

  // Dados do perfil
  const [nome, setNome] = useState("");
  const [setor, setSetor] = useState("");
  const [email, setEmail] = useState("");

  // Trocar senha
  const [senhaAtual, setSenhaAtual] = useState("");
  const [novaSenha, setNovaSenha] = useState("");
  const [confirmarSenha, setConfirmarSenha] = useState("");

  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);
  const [profileMsg, setProfileMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null);
  const [passwordMsg, setPasswordMsg] = useState<{ type: "ok" | "err"; text: string } | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    apiFetch<UserProfile>("/settings/me").then((p) => {
      setProfile(p);
      setNome(p.nome || "");
      setSetor(p.setor || "");
      setEmail(p.email);
    });
  }, [router]);

  async function handleSaveProfile(e: React.FormEvent) {
    e.preventDefault();
    setSavingProfile(true);
    setProfileMsg(null);
    try {
      await apiFetch("/settings/me", {
        method: "PUT",
        body: JSON.stringify({
          nome: nome || null,
          setor: setor || null,
          email: email || null,
        }),
      });
      setProfileMsg({ type: "ok", text: "Perfil atualizado com sucesso." });
    } catch (e) {
      setProfileMsg({ type: "err", text: (e as Error).message });
    } finally {
      setSavingProfile(false);
    }
  }

  async function handleChangePassword(e: React.FormEvent) {
    e.preventDefault();
    setPasswordMsg(null);

    if (novaSenha.length < 6) {
      setPasswordMsg({ type: "err", text: "A nova senha deve ter pelo menos 6 caracteres." });
      return;
    }
    if (novaSenha !== confirmarSenha) {
      setPasswordMsg({ type: "err", text: "As senhas nao coincidem." });
      return;
    }

    setSavingPassword(true);
    try {
      await apiFetch("/auth/change-password", {
        method: "POST",
        body: JSON.stringify({ senha_atual: senhaAtual, nova_senha: novaSenha }),
      });
      setPasswordMsg({ type: "ok", text: "Senha alterada com sucesso." });
      setSenhaAtual("");
      setNovaSenha("");
      setConfirmarSenha("");
    } catch (e) {
      setPasswordMsg({ type: "err", text: (e as Error).message });
    } finally {
      setSavingPassword(false);
    }
  }

  if (!profile) {
    return (
      <div className="min-h-screen bg-[#0f0f0f] flex items-center justify-center">
        <span className="w-8 h-8 border-2 border-[#333] border-t-blue-500 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0f0f0f]">
      <Nav />
      <main className="pt-14 px-6 max-w-2xl mx-auto py-8 space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Meu perfil</h1>
          <p className="text-gray-500 text-sm mt-1">
            Gerencie seus dados e senha de acesso
          </p>
        </div>

        {/* Informações somente leitura */}
        <Section title="Conta">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">Perfil</span>
            <span className="text-sm text-white capitalize">{profile.perfil}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-400">Status</span>
            <span
              className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                profile.status_conta === "ativo"
                  ? "bg-green-500/15 text-green-400"
                  : profile.status_conta === "pendente"
                  ? "bg-yellow-500/15 text-yellow-400"
                  : "bg-red-500/15 text-red-400"
              }`}
            >
              {profile.status_conta}
            </span>
          </div>
          {profile.telefone_vinculado && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">WhatsApp</span>
              <span className="text-sm font-mono text-blue-400">{profile.telefone_vinculado}</span>
            </div>
          )}
        </Section>

        {/* Dados editáveis */}
        <Section title="Dados pessoais" subtitle="Nome, setor e e-mail de acesso">
          <form onSubmit={handleSaveProfile} className="space-y-4">
            <InputField
              label="Nome"
              value={nome}
              onChange={setNome}
              placeholder="Seu nome completo"
            />
            <InputField
              label="Setor"
              value={setor}
              onChange={setSetor}
              placeholder="Ex: Comercial, TI, Financeiro..."
            />
            <InputField
              label="E-mail"
              type="email"
              value={email}
              onChange={setEmail}
              placeholder="seu@email.com"
              hint="Alterar o e-mail muda seu login de acesso."
            />

            {profileMsg && (
              <p className={`text-sm ${profileMsg.type === "ok" ? "text-green-400" : "text-red-400"}`}>
                {profileMsg.type === "ok" ? "✓ " : "✗ "}{profileMsg.text}
              </p>
            )}

            <button
              type="submit"
              disabled={savingProfile}
              className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 disabled:cursor-not-allowed text-white font-semibold py-2.5 rounded-xl text-sm transition-colors flex items-center justify-center gap-2"
            >
              {savingProfile ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Salvando...
                </>
              ) : (
                "Salvar dados"
              )}
            </button>
          </form>
        </Section>

        {/* Trocar senha */}
        <Section title="Alterar senha" subtitle="Informe a senha atual e a nova senha">
          <form onSubmit={handleChangePassword} className="space-y-4">
            <InputField
              label="Senha atual"
              type="password"
              value={senhaAtual}
              onChange={setSenhaAtual}
              placeholder="••••••••"
            />
            <InputField
              label="Nova senha"
              type="password"
              value={novaSenha}
              onChange={setNovaSenha}
              placeholder="Mínimo 6 caracteres"
            />
            <InputField
              label="Confirmar nova senha"
              type="password"
              value={confirmarSenha}
              onChange={setConfirmarSenha}
              placeholder="••••••••"
            />

            {passwordMsg && (
              <p className={`text-sm ${passwordMsg.type === "ok" ? "text-green-400" : "text-red-400"}`}>
                {passwordMsg.type === "ok" ? "✓ " : "✗ "}{passwordMsg.text}
              </p>
            )}

            <button
              type="submit"
              disabled={savingPassword}
              className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 disabled:cursor-not-allowed text-white font-semibold py-2.5 rounded-xl text-sm transition-colors flex items-center justify-center gap-2"
            >
              {savingPassword ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Alterando...
                </>
              ) : (
                "Alterar senha"
              )}
            </button>
          </form>
        </Section>
      </main>
    </div>
  );
}
