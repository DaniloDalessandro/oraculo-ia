from typing import Any
from pydantic import BaseModel


# ── Meta / WhatsApp Cloud API webhook schema ──────────────────────────────────

class WhatsAppWebhookPayload(BaseModel):
    object: str | None = None
    entry: list[dict[str, Any]] | None = None

    model_config = {"extra": "allow"}
