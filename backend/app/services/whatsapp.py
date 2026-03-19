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


async def send_whatsapp_buttons(
    phone: str,
    title: str,
    description: str,
    buttons: list[dict],
    footer: str = "",
) -> dict:
    """
    Send a button message via Evolution API (até 3 botões).

    Cada botão deve ter: {"id": "btn_id", "text": "Texto do botão"}

    Fallback automático para texto numerado se a API rejeitar botões nativos
    (comum em instâncias Baileys sem WhatsApp Business oficial).
    """
    if not buttons:
        return {"error": "Nenhum botão fornecido"}

    payload = {
        "number": phone,
        "title": title,
        "description": description,
        "footer": footer,
        "buttons": [
            {
                "title": "reply",
                "displayText": btn["text"],
                "id": btn["id"],
            }
            for btn in buttons[:3]  # WhatsApp permite no máximo 3 botões
        ],
    }

    result = await _post("message/sendButtons", payload)

    # Fallback: se a API rejeitar (comum em Baileys não-Business), envia como texto
    if "error" in result:
        opcoes = "\n".join(
            f"  *{i + 1}.* {btn['text']}" for i, btn in enumerate(buttons[:3])
        )
        fallback_text = f"*{title}*\n{description}\n\n{opcoes}"
        if footer:
            fallback_text += f"\n\n_{footer}_"
        return await send_whatsapp_message(phone, fallback_text)

    return result


async def send_whatsapp_cta_url(
    phone: str,
    body: str,
    button_text: str,
    url: str,
    footer: str = "",
) -> dict:
    """
    Envia mensagem com botão de URL (Call-to-Action) via Evolution API v2.

    Funciona nativamente em instâncias Cloud API (WhatsApp Business oficial).
    Em instâncias Baileys (auto-hospedado), faz fallback automático para
    texto com o link clicável, que o WhatsApp renderiza como preview tappable.
    """
    payload = {
        "number": phone,
        "title": button_text,
        "description": body,
        "footer": footer,
        "buttons": [
            {
                "title": "url",
                "displayText": button_text,
                "url": url,
            }
        ],
    }

    result = await _post("message/sendButtons", payload)

    # Fallback para instâncias Baileys que não suportam URL buttons
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
    Send a list/menu message via Evolution API.
    Melhor opção para menus com muitas opções (até 10 itens por seção).
    """
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
