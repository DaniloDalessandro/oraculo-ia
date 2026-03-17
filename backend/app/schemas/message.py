from datetime import datetime
from pydantic import BaseModel


class MessageOut(BaseModel):
    id: str
    telefone: str
    user_id: str | None
    mensagem_usuario: str
    resposta_sistema: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageListResponse(BaseModel):
    items: list[MessageOut]
    total: int
    page: int
    limit: int
