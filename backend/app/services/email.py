import logging

import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)

_HEADER = """
<div style="background:#1a2a4a;padding:32px;text-align:center;">
  <div style="font-size:40px;margin-bottom:8px;">🤖</div>
  <h1 style="color:#fff;margin:0;font-size:20px;">Oraculo IA</h1>
  <p style="color:#93b4d4;margin:4px 0 0;font-size:13px;">Plataforma corporativa</p>
</div>
"""
_FOOTER = '<div style="background:#0f0f0f;padding:16px;text-align:center;"><p style="color:#374151;font-size:11px;margin:0;">Oraculo IA &mdash; Plataforma corporativa</p></div>'
_WRAP_START = '<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8"></head><body style="margin:0;padding:0;background:#0f0f0f;font-family:Arial,sans-serif;"><div style="max-width:480px;margin:40px auto;background:#141414;border:1px solid #1e1e1e;border-radius:16px;overflow:hidden;">'
_WRAP_END = "</div></body></html>"


def _build_msg(to_email: str, subject: str, html_body: str) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    html = f"{_WRAP_START}{_HEADER}{html_body}{_FOOTER}{_WRAP_END}"
    msg.attach(MIMEText(html, "html"))
    return msg


async def _send(msg: MIMEMultipart) -> None:
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("SMTP nao configurado — e-mail nao enviado para %s", msg["To"])
        return
    await aiosmtplib.send(
        msg,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
        start_tls=True,
    )


async def send_password_reset_email(to_email: str, reset_url: str) -> None:
    body = f"""
    <div style="padding:32px;">
      <h2 style="color:#fff;font-size:18px;margin:0 0 12px;">Recuperacao de senha</h2>
      <p style="color:#9ca3af;font-size:14px;line-height:1.6;margin:0 0 24px;">
        Recebemos uma solicitacao para redefinir a senha da conta associada a este e-mail.
        Clique no botao abaixo para criar uma nova senha. O link expira em
        <strong style="color:#fff;">{settings.PASSWORD_RESET_EXPIRE_MINUTES} minutos</strong>.
      </p>
      <div style="text-align:center;margin:0 0 24px;">
        <a href="{reset_url}"
           style="display:inline-block;background:#2563eb;color:#fff;text-decoration:none;
                  padding:14px 32px;border-radius:10px;font-size:14px;font-weight:600;">
          Redefinir senha
        </a>
      </div>
      <p style="color:#6b7280;font-size:12px;line-height:1.6;margin:0;">
        Se voce nao solicitou esta recuperacao, ignore este e-mail.
      </p>
    </div>
    """
    await _send(_build_msg(to_email, "Recuperacao de senha — Oraculo IA", body))


async def send_welcome_email(to_email: str, nome: str, login_url: str) -> None:
    body = f"""
    <div style="padding:32px;">
      <h2 style="color:#fff;font-size:18px;margin:0 0 12px;">Sua conta foi criada!</h2>
      <p style="color:#9ca3af;font-size:14px;line-height:1.6;margin:0 0 16px;">
        Ola, <strong style="color:#fff;">{nome}</strong>!
        Sua conta no Oraculo IA foi criada pelo administrador.
      </p>
      <p style="color:#9ca3af;font-size:14px;line-height:1.6;margin:0 0 24px;">
        Sua conta esta <strong style="color:#facc15;">pendente de aprovacao</strong>.
        Assim que o administrador aprovar, voce receberá uma notificacao e podra acessar a plataforma.
      </p>
      <div style="text-align:center;">
        <a href="{login_url}"
           style="display:inline-block;background:#2563eb;color:#fff;text-decoration:none;
                  padding:14px 32px;border-radius:10px;font-size:14px;font-weight:600;">
          Acessar plataforma
        </a>
      </div>
    </div>
    """
    await _send(_build_msg(to_email, "Conta criada no Oraculo IA", body))


async def send_account_approved_email(to_email: str, nome: str, login_url: str) -> None:
    body = f"""
    <div style="padding:32px;">
      <h2 style="color:#fff;font-size:18px;margin:0 0 12px;">Conta aprovada!</h2>
      <p style="color:#9ca3af;font-size:14px;line-height:1.6;margin:0 0 24px;">
        Ola, <strong style="color:#fff;">{nome}</strong>!
        Sua conta foi aprovada pelo administrador. Voce ja pode acessar a plataforma.
      </p>
      <div style="text-align:center;">
        <a href="{login_url}"
           style="display:inline-block;background:#16a34a;color:#fff;text-decoration:none;
                  padding:14px 32px;border-radius:10px;font-size:14px;font-weight:600;">
          Fazer login agora
        </a>
      </div>
    </div>
    """
    await _send(_build_msg(to_email, "Conta aprovada — Oraculo IA", body))
