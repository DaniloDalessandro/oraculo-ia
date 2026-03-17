"""
Comandos pré-definidos do chatbot (sem IA).
Retorna string de resposta ou None se não for um comando reconhecido.
"""

from app.models.user import User
from app.models.user_config import UserConfig

COMMANDS = {"menu", "ajuda", "help", "status", "config", "/menu", "/ajuda", "/status", "/config"}


def is_command(text: str) -> bool:
    return text.strip().lower() in COMMANDS


async def handle_command(
    text: str,
    user: User | None,
    config: UserConfig | None,
    mensagens_hoje: int,
) -> str | None:
    cmd = text.strip().lower().lstrip("/")

    if cmd == "menu":
        return "__LIST_MENU__"

    if cmd in ("ajuda", "help"):
        return (
            "❓ *Como usar o assistente:*\n\n"
            "1️⃣ Faça login clicando no link enviado na primeira mensagem\n"
            "2️⃣ Após autenticar, envie sua pergunta normalmente\n"
            "3️⃣ Use *menu* para ver as opções disponíveis\n"
            "4️⃣ Acesse o painel web para configurações avançadas\n\n"
            "_Dúvidas? Fale com o administrador do sistema._"
        )

    if cmd == "status":
        if not user:
            return "⚠️ Você não está autenticado. Envie qualquer mensagem para receber um link de acesso."
        limite = config.limite_diario if config else 100
        pct = int((mensagens_hoje / limite) * 100) if limite else 0
        return (
            f"📊 *Seu status:*\n\n"
            f"👤 Usuário: {user.email}\n"
            f"🏷 Perfil: {user.perfil}\n"
            f"💬 Mensagens hoje: {mensagens_hoje}/{limite} ({pct}%)\n"
            f"🤖 Bot ativo: {'✅ Sim' if (config and config.bot_ativo) else '❌ Não'}\n"
            f"🧠 IA ativa: {'✅ Sim' if (config and config.ia_ativa) else '❌ Não'}"
        )

    if cmd == "config":
        if not config:
            return "⚙️ Configurações padrão ativas. Acesse o painel web para personalizar."
        return (
            f"⚙️ *Configurações atuais:*\n\n"
            f"🤖 Assistente: {config.nome_assistente}\n"
            f"🌐 Idioma: {config.idioma}\n"
            f"💬 Limite diário: {config.limite_diario} mensagens\n"
            f"🧠 Limite IA: {config.limite_ia_diario} consultas\n"
            f"📋 Nível de detalhe: {config.nivel_detalhe}\n\n"
            "_Para alterar, acesse o painel web → Configurações._"
        )

    return None
