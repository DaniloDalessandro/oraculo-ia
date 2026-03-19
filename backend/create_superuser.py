"""
Script para criar superusuário (perfil=admin) no banco de dados.

Uso:
  docker compose exec backend python create_superuser.py
"""

import asyncio
import getpass

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select

from app.config import settings
from app.database import Base
from app.models.user import User
from app.models.session import Session  # noqa: F401
from app.models.login_token import LoginToken  # noqa: F401
from app.models.message import Message  # noqa: F401
from app.models.user_config import UserConfig  # noqa: F401
from app.models.ai_query_log import AIQueryLog  # noqa: F401
from app.core.security import hash_password


async def main():
    print("=== Criar Superusuário ===\n")
    email = input("Email: ").strip()
    nome = input("Nome: ").strip()
    senha = getpass.getpass("Senha: ")
    senha_conf = getpass.getpass("Confirmar senha: ")

    if senha != senha_conf:
        print("As senhas não coincidem.")
        return

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    AsyncSess = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSess() as db:
        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            print(f"Usuário com email '{email}' já existe.")
            await engine.dispose()
            return

        user = User(
            email=email,
            nome=nome or None,
            senha_hash=hash_password(senha),
            perfil="administrador",
            status_conta="ativo",
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        print(f"\nSuperusuário criado com sucesso!")
        print(f"  ID:    {user.id}")
        print(f"  Email: {user.email}")
        print(f"  Perfil: {user.perfil}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
