"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Nav from "@/components/Nav";
import {
  apiFetch,
  getToken,
  type MessageItem,
  type MessageListResponse,
} from "@/lib/api";

function formatPhone(phone: string) {
  if (phone.length === 13)
    return `+${phone.slice(0, 2)} (${phone.slice(2, 4)}) ${phone.slice(4, 9)}-${phone.slice(9)}`;
  return phone;
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

export default function HistoryPage() {
  const router = useRouter();
  const [items, setItems] = useState<MessageItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  const limit = 20;
  const totalPages = Math.ceil(total / limit);

  const load = useCallback(
    async (p: number, query: string) => {
      setLoading(true);
      try {
        const params = new URLSearchParams({
          page: String(p),
          limit: String(limit),
        });
        if (query) params.set("q", query);
        const data = await apiFetch<MessageListResponse>(
          `/messages?${params.toString()}`
        );
        setItems(data.items);
        setTotal(data.total);
      } catch {
        // 401 handled in apiFetch
      } finally {
        setLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    load(page, search);
  }, [router, page, search, load]);

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    setSearch(q);
  }

  return (
    <div className="min-h-screen bg-[#0f0f0f]">
      <Nav />
      <main className="pt-14 px-6 max-w-5xl mx-auto py-8">
        {/* Header */}
        <div className="flex items-start justify-between mb-8 flex-wrap gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white">Histórico</h1>
            <p className="text-gray-500 text-sm mt-1">
              {total} mensagem{total !== 1 ? "s" : ""} no total
            </p>
          </div>

          {/* Search */}
          <form onSubmit={handleSearch} className="flex gap-2">
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Buscar mensagens..."
              className="bg-[#141414] border border-[#222] rounded-xl px-4 py-2 text-white text-sm placeholder-gray-600 focus:outline-none focus:border-blue-500 w-64"
            />
            <button
              type="submit"
              className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-xl text-sm font-medium transition-colors"
            >
              Buscar
            </button>
            {search && (
              <button
                type="button"
                onClick={() => {
                  setQ("");
                  setSearch("");
                  setPage(1);
                }}
                className="text-gray-500 hover:text-white text-sm px-2 transition-colors"
              >
                Limpar
              </button>
            )}
          </form>
        </div>

        {/* Table */}
        <div className="bg-[#141414] border border-[#222] rounded-xl overflow-hidden">
          {loading ? (
            <div className="flex justify-center py-16">
              <span className="w-7 h-7 border-2 border-[#333] border-t-blue-500 rounded-full animate-spin" />
            </div>
          ) : items.length === 0 ? (
            <div className="py-16 text-center text-gray-600 text-sm">
              {search
                ? `Nenhum resultado para "${search}"`
                : "Nenhuma mensagem ainda."}
            </div>
          ) : (
            <div className="divide-y divide-[#1e1e1e]">
              {/* Header row */}
              <div className="grid grid-cols-[140px_1fr_1fr_100px] gap-4 px-6 py-3 text-xs text-gray-600 uppercase tracking-wide">
                <span>Telefone</span>
                <span>Mensagem</span>
                <span>Resposta</span>
                <span className="text-right">Data</span>
              </div>

              {items.map((item) => (
                <div key={item.id}>
                  <button
                    onClick={() =>
                      setExpanded(expanded === item.id ? null : item.id)
                    }
                    className="w-full grid grid-cols-[140px_1fr_1fr_100px] gap-4 px-6 py-4 text-left hover:bg-white/5 transition-colors"
                  >
                    <span className="text-xs font-mono text-blue-400 truncate">
                      {formatPhone(item.telefone)}
                    </span>
                    <span className="text-sm text-gray-300 truncate">
                      {item.mensagem_usuario}
                    </span>
                    <span className="text-sm text-gray-500 truncate">
                      {item.resposta_sistema}
                    </span>
                    <span className="text-xs text-gray-600 text-right">
                      {formatDate(item.created_at)}
                    </span>
                  </button>

                  {/* Expanded detail */}
                  {expanded === item.id && (
                    <div className="px-6 pb-5 bg-[#111] border-t border-[#1e1e1e] space-y-3">
                      <div>
                        <p className="text-xs text-gray-600 mb-1">
                          Mensagem do usuário:
                        </p>
                        <p className="text-sm text-gray-200 whitespace-pre-wrap">
                          {item.mensagem_usuario}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-600 mb-1">
                          Resposta do sistema:
                        </p>
                        <p className="text-sm text-gray-400 whitespace-pre-wrap">
                          {item.resposta_sistema}
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2 mt-6">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1.5 rounded-lg text-sm text-gray-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              ← Anterior
            </button>
            <span className="text-sm text-gray-600">
              {page} / {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-3 py-1.5 rounded-lg text-sm text-gray-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              Próxima →
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
