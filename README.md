# Oráculo IA

Chatbot corporativo SaaS integrado ao WhatsApp via **Meta Cloud API**. Responde perguntas com IA (Text-to-SQL), processa mensagens de forma assíncrona com Celery e oferece painel web de gerenciamento com configurações de sistema editáveis via interface.

## Stack

- **Backend:** FastAPI, PostgreSQL, Redis, SQLAlchemy async, Alembic
- **IA:** Groq (llama-3.3-70b-versatile) · Google Gemini (gemini-2.0-flash) · OpenAI (gpt-4o-mini) — configurável via painel
- **Filas:** Celery + Redis (fila_ia, fila_mensagens)
- **Frontend:** Next.js 15, React 19, Tailwind CSS
- **WhatsApp:** Meta Cloud API (webhook oficial)
- **Infra:** Docker, Traefik (SSL automático), GHCR, GitHub Actions CI/CD

## Início rápido (local)

```bash
cp .env.example .env   # ajuste as variáveis
docker compose up --build
```

| Serviço | URL |
|---------|-----|
| Frontend | http://localhost:3001 |
| Backend / Swagger | http://localhost:8001/docs |
| Flower (Celery) | http://localhost:5555 |

## Produção

A aplicação fica disponível em:

```
https://oraculo.82-25-75-110.sslip.io
```

O domínio usa **sslip.io** — DNS gratuito que resolve automaticamente para o IP da VPS, sem registro necessário. SSL é gerenciado pelo Traefik via Let's Encrypt.

## Configuração mínima (.env)

```env
SECRET_KEY=troque-em-producao

# WhatsApp — Meta Cloud API
WHATSAPP_TOKEN=seu-token
WHATSAPP_PHONE_NUMBER_ID=seu-phone-id
WHATSAPP_VERIFY_TOKEN=seu-verify-token
WHATSAPP_WABA_ID=seu-waba-id
WHATSAPP_APP_ID=seu-app-id
WHATSAPP_APP_SECRET=seu-app-secret

# IA (ao menos um)
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=AIza...
OPENAI_API_KEY=sk-...

APP_URL=https://oraculo.82-25-75-110.sslip.io
```

Todas as configurações de IA (provider ativo, modelos, tokens, temperatura, cache, rate limit, etc.) podem ser alteradas sem reiniciar o servidor via **Configurações > Sistema** no painel admin.

## Configurando o WhatsApp

### 1. Criar superusuário

```bash
docker compose exec backend python create_superuser.py
```

Ou defina `ADMIN_EMAIL` e `ADMIN_SENHA` no `.env` — o usuário é criado automaticamente na primeira inicialização.

### 2. Configurar webhook na Meta

No [Meta for Developers](https://developers.facebook.com/), configure o webhook do seu app para apontar para:

```
https://oraculo.82-25-75-110.sslip.io/api/webhook/whatsapp
```

Eventos necessários: `messages`

### 3. Rodar migrations

```bash
docker compose exec backend alembic upgrade head
```

## Deploy (CI/CD)

Cada push para `main` dispara o GitHub Actions que:

1. Builda as imagens `backend` e `frontend`
2. Publica no GHCR (`ghcr.io/danilodalessandro/oraculo-ia-*:latest`)
3. SSHa na VPS, atualiza o `docker-compose.yml` com as novas imagens e reinicia os containers

Segredos necessários no GitHub: `VPS_HOST`, `VPS_USER`, `VPS_SSH_PRIVATE_KEY`.

## Estrutura

```
oraculo-ia/
├── backend/
│   ├── app/
│   │   ├── routers/      # endpoints FastAPI
│   │   ├── services/     # lógica de negócio, IA, cache, rate limit
│   │   ├── models/       # ORM SQLAlchemy
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── core/         # segurança e dependências
│   │   └── worker/       # Celery tasks
│   └── alembic/          # migrations
├── frontend/src/app/     # páginas Next.js
├── deploy/               # compose e scripts de produção
├── .github/workflows/    # CI/CD GitHub Actions
├── docker-compose.yml    # desenvolvimento local
└── .env
```

## Fluxo de mensagens

1. Usuário manda mensagem no WhatsApp
2. Webhook recebe → verifica sessão → aplica rate limit
3. Se não autenticado: envia link de login
4. Se autenticado: enfileira task no Celery → worker processa com IA (Text-to-SQL) → responde
