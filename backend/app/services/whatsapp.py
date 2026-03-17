import httpx
from app.config import settings


async def _post(path: str, payload: dict) -> dict:
    url = f"{settings.EVOLUTION_API_URL}/{path}/{settings.EVOLUTION_INSTANCE_NAME}"
    headers = {"apikey": settings.EVOLUTION_API_KEY, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            print(f"[WhatsApp] Falha ao enviar para {payload.get('number')}: {exc}")
            return {"error": str(exc)}


async def send_whatsapp_message(phone: str, message: str) -> dict:
    """Send a text message via Evolution API."""
    return await _post("message/sendText", {"number": phone, "textMessage": {"text": message}})




async def send_whatsapp_list(
    phone: str,
    title: str,
    description: str,
    button_text: str,
    sections: list[dict],
    footer: str = "",
) -> dict:
    """Send a list/menu message via Evolution API."""
    payload = {
        "number": phone,
        "listMessage": {
            "title": title,
            "description": description,
            "footerText": footer,
            "buttonText": button_text,
            "sections": sections,
        },
    }
    return await _post("message/sendList", payload)


def normalize_phone(raw: str) -> str:
    """
    Normaliza o JID do WhatsApp para uso como identificador.
    Preserva o sufixo @lid para contatos com ID interno do WhatsApp.
    Remove apenas @s.whatsapp.net e sufixos de dispositivo (:N@).
    """
    # Contatos com @lid precisam do JID completo para envio
    if "@lid" in raw:
        return raw.split(":")[0]  # remove :N se houver, mantém @lid

    # Número normal: remove @s.whatsapp.net e sufixo de dispositivo
    phone = raw.split("@")[0]
    phone = phone.split(":")[0]
    return phone.strip()
