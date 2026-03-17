const API_BASE = "/api";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

export function clearToken(): void {
  localStorage.removeItem("access_token");
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    clearToken();
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail || `HTTP ${res.status}`);
  }

  return res.json() as Promise<T>;
}

// ── Typed API helpers ────────────────────────────────────────────────────────

export interface DashboardStats {
  total_mensagens: number;
  usuarios_ativos: number;
  mensagens_hoje: number;
  whatsapp_conectado: boolean;
  ultimas_mensagens: RecentMessage[];
  // Sprint 4
  total_ia_hoje: number;
  tempo_medio_resposta_ms: number;
  taxa_erro_ia_pct: number;
  workers_ativos: number;
  cache_hit_rate: number;
}

export interface RecentMessage {
  telefone: string;
  mensagem_usuario: string;
  resposta_sistema: string;
  created_at: string;
}

export interface UserProfile {
  id: string;
  email: string;
  nome: string | null;
  perfil: string;
  status_conta: string;
  telefone_vinculado: string | null;
  config: UserConfig | null;
}

export interface UserConfig {
  bot_ativo: boolean;
  limite_diario: number;
  idioma: string;
  nome_assistente: string;
  // Sprint 3
  ia_ativa: boolean;
  limite_ia_diario: number;
  nivel_detalhe: string;
}

export interface MessageItem {
  id: string;
  telefone: string;
  user_id: string | null;
  mensagem_usuario: string;
  resposta_sistema: string;
  created_at: string;
}

export interface MessageListResponse {
  items: MessageItem[];
  total: number;
  page: number;
  limit: number;
}
