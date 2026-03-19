"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearToken } from "@/lib/api";
import {
  LayoutDashboard,
  MessageSquare,
  Bot,
  Settings,
  Users,
  LogOut,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";

const links = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/history", label: "Histórico", icon: MessageSquare },
  { href: "/ai-logs", label: "Logs IA", icon: Bot },
  { href: "/settings", label: "Configurações", icon: Settings },
  { href: "/usuarios", label: "Usuários", icon: Users },
];

export default function Nav() {
  const pathname = usePathname();
  const router = useRouter();

  function handleLogout() {
    clearToken();
    router.push("/login");
  }

  return (
    <nav className="fixed left-0 right-0 top-0 z-50 h-14 border-b border-border bg-background/80 backdrop-blur-sm">
      <div className="mx-auto flex h-full max-w-7xl items-center gap-2 px-4 sm:px-6 lg:px-8">
        {/* Brand */}
        <Link
          href="/dashboard"
          className="mr-4 flex shrink-0 items-center gap-2 text-sm font-semibold tracking-tight"
        >
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-600">
            <Zap className="h-4 w-4 text-white" />
          </div>
          <span className="hidden sm:inline">Oráculo IA</span>
        </Link>

        {/* Links */}
        <div className="flex flex-1 items-center gap-0.5 overflow-x-auto">
          {links.map((l) => {
            const active = pathname.startsWith(l.href);
            const Icon = l.icon;
            return (
              <Link
                key={l.href}
                href={l.href}
                className={cn(
                  "flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm transition-colors",
                  active
                    ? "bg-blue-500/15 text-blue-400"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                <Icon className="h-4 w-4" />
                <span className="hidden md:inline">{l.label}</span>
              </Link>
            );
          })}
        </div>

        {/* Logout */}
        <button
          onClick={handleLogout}
          className="flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-red-500/10 hover:text-red-400"
          aria-label="Sair da conta"
        >
          <LogOut className="h-4 w-4" />
          <span className="hidden sm:inline">Sair</span>
        </button>
      </div>
    </nav>
  );
}
