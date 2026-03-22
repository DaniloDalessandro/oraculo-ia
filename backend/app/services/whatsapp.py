import httpx
from app.config import settings

_BASE = "https://graph.facebook.com/{version}/{phone_number_id}/messages"


def _url() -> str:
    return _BASE.format(
        version=settings.WHATSAPP_API_VERSION,
        phone_number_id=settings.WHATSAPP_PHONE_NUMBER_ID,
    )


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }


async def _post(payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(_url(), json=payload, headers=_headers())
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            to = payload.get("to", "?")
            # Mascara token no log para evitar vazamento (issue #12)
            err_str = str(exc).replace(settings.WHATSAPP_TOKEN, "***TOKEN***")
            print(f"[WhatsApp] Falha ao enviar para {to}: {err_str}")
            return {"error": err_str}


async def send_whatsapp_message(phone: str, message: str) -> dict:
    """Envia mensagem de texto simples via WhatsApp Cloud API."""
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": message},
    }
    return await _post(payload)


async def send_whatsapp_buttons(
    phone: str,
    title: str,
    description: str,
    buttons: list[dict],
    footer: str = "",
) -> dict:
    """
    Envia mensagem com botões interativos via WhatsApp Cloud API (até 3 botões).
    Cada botão deve ter: {"id": "btn_id", "text": "Texto do botão"}
    """
    if not buttons:
        return {"error": "Nenhum botão fornecido"}

    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "header": {"type": "text", "text": title},
            "body": {"text": description},
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": btn["id"],
                            "title": btn["text"][:20],  # Cloud API: max 20 chars
                        },
                    }
                    for btn in buttons[:3]
                ]
            },
        },
    }
    if footer:
        payload["interactive"]["footer"] = {"text": footer}

    return await _post(payload)


async def send_whatsapp_cta_url(
    phone: str,
    body: str,
    button_text: str,
    url: str,
    footer: str = "",
) -> dict:
    """
    Envia mensagem com botão de URL (Call-to-Action) via WhatsApp Cloud API.
    Requer conta WhatsApp Business verificada.
    """
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": {
            "type": "cta_url",
            "body": {"text": body},
            "action": {
                "name": "cta_url",
                "parameters": {
                    "display_text": button_text,
                    "url": url,
                },
            },
        },
    }
    if footer:
        payload["interactive"]["footer"] = {"text": footer}

    result = await _post(payload)

    # Fallback: se a conta não suportar cta_url, envia texto com link
    if "error" in result:
        fallback_text = f"{body}\n\n🔗 {url}"
        if footer:
            fallback_text += f"\n\n_{footer}_"
        return await send_whatsapp_message(phone, fallback_text)

    return result


async def send_whatsapp_list(
    phone: str,
    title: str,
    description: str,
    button_text: str,
    sections: list[dict],
    footer: str = "",
) -> dict:
    """
    Envia mensagem de lista interativa via WhatsApp Cloud API.
    sections: [{"title": "...", "rows": [{"id": "...", "title": "...", "description": "..."}]}]
    """
    # Adapta formato Evolution -> Cloud API (rowId -> id)
    adapted_sections = []
    for section in sections:
        rows = []
        for row in section.get("rows", []):
            rows.append({
                "id": row.get("rowId") or row.get("id", ""),
                "title": row.get("title", "")[:24],  # Cloud API: max 24 chars
                "description": row.get("description", "")[:72],
            })
        adapted_sections.append({"title": section.get("title", ""), "rows": rows})

    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": title},
            "body": {"text": description},
            "action": {
                "button": button_text[:20],
                "sections": adapted_sections,
            },
        },
    }
    if footer:
        payload["interactive"]["footer"] = {"text": footer}

    return await _post(payload)


def normalize_phone(raw: str) -> str:
    """
    Normaliza número do webhook da Meta.
    A Cloud API envia números no formato internacional sem '+' (ex: 5511999999999).
    """
    phone = raw.strip().lstrip("+")
    return phone
