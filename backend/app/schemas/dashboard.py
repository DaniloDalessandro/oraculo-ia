from datetime import datetime
from pydantic import BaseModel


class RecentMessage(BaseModel):
    telefone: str
    mensagem_usuario: str
    resposta_sistema: str
    created_at: datetime


class DashboardStats(BaseModel):
    total_mensagens: int
    usuarios_ativos: int
    mensagens_hoje: int
    whatsapp_conectado: bool
    ultimas_mensagens: list[RecentMessage]
    # Sprint 4
    total_ia_hoje: int = 0
    tempo_medio_resposta_ms: float = 0.0
    taxa_erro_ia_pct: float = 0.0
    workers_ativos: int = 0
    cache_hit_rate: float = 0.0
