from typing import Any
from pydantic import BaseModel


class EvolutionWebhookPayload(BaseModel):
    event: str | None = None
    instance: str | None = None
    data: dict[str, Any] | None = None

    model_config = {"extra": "allow"}
