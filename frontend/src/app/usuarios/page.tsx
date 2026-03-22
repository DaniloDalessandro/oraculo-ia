"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Nav from "@/components/Nav";
import { apiFetch, getToken, type AdminUser, type AdminUserCreate } from "@/lib/api";

// ── Status badge ─────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    ativo: "bg-green-500/15 text-green-400 border-green-500/20",
    inativo: "bg-red-500/15 text-red-400 border-red-500/20",
  };
  const labels: Record<string, string> = {
    ativo: "Ativo",
    inativo: "Inativo",
  };
  const cls = styles[status] ?? "bg-gray-500/15 text-gray-400 border-gray-500/20";
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${cls}`}>
      {labels[status] ?? status}
    </span>
  );
}

// ── Modal para criar usuário ──────────────────────────────────────────────────

interface CreateModalProps {
  onClose: () => void;
  onCreated: () => void;
}

function CreateModal({ onClose, onCreated }: CreateModalProps) {
  const [form, setForm] = useState<AdminUserCreate>({
    email: "",
    senha: "",
    nome: "",
    setor: "",
    perfil: "colaborador",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function handleChange(e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await apiFetch<AdminUser>("/admin/usuarios", {
        method: "POST",
        body: JSON.stringify(form),
      });
      onCreated();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erro ao criar usuário");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-[#141414] border border-[#222] rounded-xl w-full max-w-md p-6 shadow-2xl">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-white font-semibold text-base">Novo Usuário</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-white transition-colors text-lg leading-none"
          >
            ×
          </button>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-red-400 text-sm mb-4">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Nome</label>
            <input
              name="nome"
              value={form.nome}
              onChange={handleChange}
              required
              className="w-full bg-[#1a1a1a] border border-[#333] rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 transition-colors"
              placeholder="Nome completo"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Email</label>
            <input
              name="email"
              type="email"
              value={form.email}
              onChange={handleChange}
              required
              className="w-full bg-[#1a1a1a] border border-[#333] rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 transition-colors"
              placeholder="usuario@empresa.com"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Senha</label>
            <input
              name="senha"
              type="password"
              value={form.senha}
              onChange={handleChange}
              required
              className="w-full bg-[#1a1a1a] border border-[#333] rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 transition-colors"
              placeholder="Senha inicial"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Setor</label>
            <input
              name="setor"
              value={form.setor}
              onChange={handleChange}
              required
              className="w-full bg-[#1a1a1a] border border-[#333] rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 transition-colors"
              placeholder="Ex: Vendas, TI, RH"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Perfil</label>
            <select
              name="perfil"
              value={form.perfil}
              onChange={handleChange}
              className="w-full bg-[#1a1a1a] border border-[#333] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500 transition-colors"
            >
              <option value="colaborador">Colaborador</option>
              <option value="administrador">Administrador</option>
            </select>
          </div>

          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 rounded-lg border border-[#333] text-sm text-gray-400 hover:text-white hover:border-[#555] transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-sm text-white font-medium transition-colors"
            >
              {loading ? "Criando..." : "Criar Usuário"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function UsuariosPage() {
  const router = useRouter();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  async function fetchUsers() {
    try {
      const data = await apiFetch<AdminUser[]>("/admin/usuarios");
      setUsers(data);
      setError("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Erro ao carregar usuários");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    fetchUsers();
  }, [router]);

  async function handleStatusChange(userId: string, newStatus: string) {
    setActionLoading(userId + newStatus);
    try {
      await apiFetch<AdminUser>(`/admin/usuarios/${userId}`, {
        method: "PATCH",
        body: JSON.stringify({ status_conta: newStatus }),
      });
      await fetchUsers();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Erro ao atualizar status");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleDelete(userId: string, nome: string | null) {
    const confirmed = window.confirm(
      `Tem certeza que deseja excluir o usuário "${nome ?? userId}"? Esta ação não pode ser desfeita.`
    );
    if (!confirmed) return;

    setActionLoading(userId + "delete");
    try {
      await apiFetch(`/admin/usuarios/${userId}`, { method: "DELETE" });
      await fetchUsers();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Erro ao excluir usuário");
    } finally {
      setActionLoading(null);
    }
  }

  function formatDate(iso: string) {
    return new Date(iso).toLocaleString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  return (
    <div className="min-h-screen bg-[#0f0f0f]">
      <Nav />
      <main className="pt-14 px-6 max-w-7xl mx-auto py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-white">Usuários</h1>
            <p className="text-gray-500 text-sm mt-1">
              Gerencie os usuários do sistema
            </p>
          </div>
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors"
          >
            <span>+</span>
            Novo Usuário
          </button>
        </div>

        {/* Loading */}
        {loading && (
          <div className="flex justify-center py-20">
            <span className="w-8 h-8 border-2 border-[#333] border-t-blue-500 rounded-full animate-spin" />
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Table */}
        {!loading && !error && (
          <div className="bg-[#141414] border border-[#222] rounded-xl overflow-hidden">
            {users.length === 0 ? (
              <div className="px-6 py-16 text-center text-gray-600 text-sm">
                Nenhum usuário cadastrado. Clique em "Novo Usuário" para começar.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[#222]">
                      <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
                        Nome
                      </th>
                      <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
                        Email
                      </th>
                      <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
                        Setor
                      </th>
                      <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
                        Perfil
                      </th>
                      <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
                        Status
                      </th>
                      <th className="text-left px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
                        Criado em
                      </th>
                      <th className="text-right px-5 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">
                        Ações
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#1e1e1e]">
                    {users.map((user) => {
                      const isLoading = actionLoading?.startsWith(user.id);
                      return (
                        <tr key={user.id} className="hover:bg-white/[0.02] transition-colors">
                          <td className="px-5 py-4 text-white font-medium">
                            {user.nome ?? <span className="text-gray-600 italic">—</span>}
                          </td>
                          <td className="px-5 py-4 text-gray-300 font-mono text-xs">
                            {user.email}
                          </td>
                          <td className="px-5 py-4 text-gray-400">
                            {user.setor ?? <span className="text-gray-600 italic">—</span>}
                          </td>
                          <td className="px-5 py-4">
                            <span className={`text-xs font-medium ${
                              user.perfil === "administrador" ? "text-purple-400" : "text-blue-400"
                            }`}>
                              {user.perfil === "administrador" ? "Administrador" : "Colaborador"}
                            </span>
                          </td>
                          <td className="px-5 py-4">
                            <StatusBadge status={user.status_conta} />
                          </td>
                          <td className="px-5 py-4 text-gray-500 text-xs">
                            {formatDate(user.created_at)}
                          </td>
                          <td className="px-5 py-4">
                            <div className="flex items-center justify-end gap-2">
                              {/* Status action button */}
                              {user.status_conta === "ativo" && (
                                <button
                                  onClick={() => handleStatusChange(user.id, "inativo")}
                                  disabled={!!isLoading}
                                  className="px-2.5 py-1 bg-red-600/20 hover:bg-red-600/30 text-red-400 border border-red-600/20 rounded text-xs font-medium transition-colors disabled:opacity-50"
                                >
                                  Desativar
                                </button>
                              )}
                              {user.status_conta === "inativo" && (
                                <button
                                  onClick={() => handleStatusChange(user.id, "ativo")}
                                  disabled={!!isLoading}
                                  className="px-2.5 py-1 bg-green-600/20 hover:bg-green-600/30 text-green-400 border border-green-600/20 rounded text-xs font-medium transition-colors disabled:opacity-50"
                                >
                                  Ativar
                                </button>
                              )}

                              {/* Delete button */}
                              <button
                                onClick={() => handleDelete(user.id, user.nome)}
                                disabled={!!isLoading}
                                className="px-2.5 py-1 bg-red-600/10 hover:bg-red-600/20 text-red-500 border border-red-600/15 rounded text-xs font-medium transition-colors disabled:opacity-50"
                              >
                                Excluir
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Create user modal */}
      {showModal && (
        <CreateModal
          onClose={() => setShowModal(false)}
          onCreated={() => {
            setShowModal(false);
            fetchUsers();
          }}
        />
      )}
    </div>
  );
}
