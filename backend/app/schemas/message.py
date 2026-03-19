from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class MessageOut(BaseModel):
    id: UUID
    telefone: str
    user_id: UUID | None
    mensagem_usuario: str
    resposta_sistema: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageListResponse(BaseModel):
    items: list[MessageOut]
    total: int
    page: int
    limit: int
