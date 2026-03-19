"use client";

import { clearToken } from "@/lib/api";
import { useRouter } from "next/navigation";

export default function AcessoNegadoPage() {
  const router = useRouter();

  function handleLogout() {
    clearToken();
    router.push("/login");
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-[#0f0f0f] p-4">
      <div className="text-center max-w-sm">
        <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center text-3xl mx-auto mb-6">
          🔒
        </div>
        <h1 className="text-xl font-bold text-white mb-2">Sem permissão</h1>
        <p className="text-gray-400 text-sm mb-6">
          Sua conta é do perfil <span className="text-white font-medium">Colaborador</span> e não tem
          acesso ao painel web. Use o WhatsApp para interagir com o assistente.
        </p>
        <button
          onClick={handleLogout}
          className="px-4 py-2 bg-[#1e1e1e] hover:bg-[#252525] border border-[#333] text-gray-300 text-sm rounded-lg transition-colors"
        >
          Sair
        </button>
      </div>
    </main>
  );
}
