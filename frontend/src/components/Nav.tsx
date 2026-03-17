"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearToken } from "@/lib/api";

const links = [
  { href: "/dashboard", label: "Dashboard", icon: "📊" },
  { href: "/history", label: "Histórico", icon: "💬" },
  { href: "/ai-logs", label: "Logs IA", icon: "🤖" },
{ href: "/settings", label: "Configurações", icon: "⚙️" },
];

export default function Nav() {
  const pathname = usePathname();
  const router = useRouter();

  function handleLogout() {
    clearToken();
    router.push("/login");
  }

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 h-14 bg-[#111] border-b border-[#222] flex items-center px-6 gap-6">
      <span className="text-white font-bold text-sm tracking-wide mr-4">
        🤖 Oráculo IA
      </span>

      <div className="flex items-center gap-1 flex-1">
        {links.map((l) => {
          const active = pathname.startsWith(l.href);
          return (
            <Link
              key={l.href}
              href={l.href}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                active
                  ? "bg-blue-600/20 text-blue-400"
                  : "text-gray-400 hover:text-white hover:bg-white/5"
              }`}
            >
              <span>{l.icon}</span>
              {l.label}
            </Link>
          );
        })}
      </div>

      <button
        onClick={handleLogout}
        className="text-xs text-gray-500 hover:text-red-400 transition-colors"
      >
        Sair
      </button>
    </nav>
  );
}
