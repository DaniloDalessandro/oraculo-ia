"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Nav from "@/components/Nav";
import { apiFetch, getToken } from "@/lib/api";

interface AILogItem {
  id: string;
  user_id: string | null;
  telefone: string;
  pergunta_original: string;
  sql_gerado: string | null;
  resposta_final: string | null;
  tempo_execucao_ms: number | null;
  modelo_usado: string;
  erro: string | null;
  created_at: string;
}

interface AILogListResponse {
  items: AILogItem[];
  total: number;
  page: number;
  limit: number;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function StatusBadge({ erro }: { erro: string | null }) {
  if (erro) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-red-500/10 text-red-400">
        ● Erro
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-green-500/10 text-green-400">
      ● OK
    </span>
  );
}

export default function AILogsPage() {
  const router = useRouter();
  const [items, setItems] = useState<AILogItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [comErro, setComErro] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  const limit = 20;
  const totalPages = Math.ceil(total / limit);

  const load = useCallback(
    async (p: number, erroFilter: boolean | null) => {
      setLoading(true);
      try {
        const params = new URLSearchParams({
          page: String(p),
          limit: String(limit),
        });
        if (erroFilter !== null) params.set("com_erro", String(erroFilter));
        const data = await apiFetch<AILogListResponse>(
          `/ai-logs?${params.toString()}`
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
    load(page, comErro);
  }, [router, page, comErro, load]);

  return (
    <div className="min-h-screen bg-[#0f0f0f]">
      <Nav />
      <main className="pt-14 px-6 max-w-7xl mx-auto py-8">
        {/* Header */}
        <div className="flex items-start justify-between mb-8 flex-wrap gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white">Logs de IA</h1>
            <p className="text-gray-500 text-sm mt-1">
              {total} consulta{total !== 1 ? "s" : ""} registrada
              {total !== 1 ? "s" : ""}
            </p>
          </div>

          {/* Filtros */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-600">Filtrar:</span>
            {[
              { label: "Todos", value: null },
              { label: "Sucesso", value: false },
              { label: "Com erro", value: true },
            ].map((f) => (
              <button
                key={String(f.value)}
                onClick={() => {
                  setComErro(f.value);
                  setPage(1);
                }}
                className={`px-3 py-1.5 rounded-lg text-xs transition-colors ${
                  comErro === f.value
                    ? "bg-blue-600 text-white"
                    : "bg-[#1a1a1a] text-gray-400 hover:text-white"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {/* Table */}
        <div className="bg-[#141414] border border-[#222] rounded-xl overflow-hidden">
          {loading ? (
            <div className="flex justify-center py-16">
              <span className="w-7 h-7 border-2 border-[#333] border-t-blue-500 rounded-full animate-spin" />
            </div>
          ) : items.length === 0 ? (
            <div className="py-16 text-center text-gray-600 text-sm">
              Nenhum log registrado ainda.
            </div>
          ) : (
            <div className="divide-y divide-[#1e1e1e]">
              {/* Header */}
              <div className="grid grid-cols-[160px_1fr_100px_90px_120px] gap-3 px-6 py-3 text-xs text-gray-600 uppercase tracking-wide">
                <span>Telefone</span>
                <span>Pergunta</span>
                <span>Tempo</span>
                <span>Status</span>
                <span className="text-right">Data</span>
              </div>

              {items.map((item) => (
                <div key={item.id}>
                  <button
                    onClick={() =>
                      setExpanded(expanded === item.id ? null : item.id)
                    }
                    className="w-full grid grid-cols-[160px_1fr_100px_90px_120px] gap-3 px-6 py-4 text-left hover:bg-white/5 transition-colors"
                  >
                    <span className="text-xs font-mono text-blue-400 truncate">
                      {item.telefone}
                    </span>
                    <span className="text-sm text-gray-300 truncate">
                      {item.pergunta_original}
                    </span>
                    <span className="text-xs text-gray-500">
                      {item.tempo_execucao_ms != null
                        ? `${item.tempo_execucao_ms}ms`
                        : "—"}
                    </span>
                    <span>
                      <StatusBadge erro={item.erro} />
                    </span>
                    <span className="text-xs text-gray-600 text-right">
                      {formatDate(item.created_at)}
                    </span>
                  </button>

                  {/* Expanded */}
                  {expanded === item.id && (
                    <div className="px-6 pb-5 bg-[#111] border-t border-[#1e1e1e] space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <p className="text-xs text-gray-600 mb-1">Pergunta original:</p>
                          <p className="text-sm text-gray-200">
                            {item.pergunta_original}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs text-gray-600 mb-1">Modelo:</p>
                          <p className="text-xs font-mono text-purple-400">
                            {item.modelo_usado}
                          </p>
                        </div>
                      </div>

                      {item.sql_gerado && (
                        <div>
                          <p className="text-xs text-gray-600 mb-1">SQL gerado:</p>
                          <pre className="bg-[#0a0a0a] border border-[#222] rounded-lg p-3 text-xs text-green-400 overflow-x-auto whitespace-pre-wrap">
                            {item.sql_gerado}
                          </pre>
                        </div>
                      )}

                      {item.resposta_final && (
                        <div>
                          <p className="text-xs text-gray-600 mb-1">Resposta enviada:</p>
                          <p className="text-sm text-gray-300 whitespace-pre-wrap bg-[#0a0a0a] border border-[#222] rounded-lg p-3">
                            {item.resposta_final}
                          </p>
                        </div>
                      )}

                      {item.erro && (
                        <div>
                          <p className="text-xs text-gray-600 mb-1">Erro:</p>
                          <p className="text-xs text-red-400 bg-red-500/5 border border-red-500/20 rounded-lg p-3">
                            {item.erro}
                          </p>
                        </div>
                      )}
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
              className="px-3 py-1.5 rounded-lg text-sm text-gray-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed"
            >
              ← Anterior
            </button>
            <span className="text-sm text-gray-600">
              {page} / {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-3 py-1.5 rounded-lg text-sm text-gray-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed"
            >
              Próxima →
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
