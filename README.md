# Oráculo IA

Chatbot corporativo SaaS integrado ao WhatsApp via Evolution API. Responde perguntas com IA (Text-to-SQL), processa mensagens de forma assíncrona com Celery e oferece painel web de gerenciamento.

## Stack

- **Backend:** FastAPI, PostgreSQL, Redis, SQLAlchemy async, Alembic
- **IA:** LangChain + OpenAI (gpt-4o-mini), Text-to-SQL
- **Filas:** Celery + Redis (fila_ia, fila_mensagens)
- **Frontend:** Next.js 15, React 19, Tailwind CSS
- **WhatsApp:** Evolution API (webhook)

## Início rápido

```bash
cp .env.example .env   # ajuste as variáveis
docker compose up --build
```

| Serviço | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend / Swagger | http://localhost:8000/docs |
| Flower (Celery) | http://localhost:5555 |
| Evolution API | http://localhost:8080 |
| Evolution Manager | http://localhost:8080/manager |

## Configuração mínima (.env)

```env
OPENAI_API_KEY=sk-...
EVOLUTION_API_URL=http://seu-servidor:8080
EVOLUTION_API_KEY=sua-chave
EVOLUTION_INSTANCE_NAME=oraculo
APP_URL=http://localhost:3000
SECRET_KEY=troque-em-producao
```

## Configurando o WhatsApp

### 1. Criar superusuário
```bash
docker compose exec backend python create_superuser.py
```

### 2. Criar instância e conectar WhatsApp

**Opção A — Manager Web (recomendado):**

Acesse http://localhost:8080/manager e faça login com a `EVOLUTION_API_KEY` do `.env`.
Na interface, localize a instância `oraculo` e clique em **Connect** para exibir o QR Code na tela.

**Opção B — PowerShell:**
```powershell
# Criar instância
Invoke-RestMethod -Method Post -Uri "http://localhost:8080/instance/create" `
  -Headers @{ "apikey"="SUA_CHAVE"; "Content-Type"="application/json" } `
  -Body '{"instanceName": "oraculo", "qrcode": true}'

# Gerar e abrir QR code
$r = Invoke-RestMethod -Uri "http://localhost:8080/instance/connect/oraculo" -Headers @{ "apikey"="SUA_CHAVE" }
$b = $r.qrcode.base64 -replace "data:image/png;base64,",""
[IO.File]::WriteAllBytes("$env:USERPROFILE\qrcode.png", [Convert]::FromBase64String($b))
Start-Process "$env:USERPROFILE\qrcode.png"
```
Escaneie o QR code com o WhatsApp do número que será o bot.

### 3. Configurar webhook
```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8080/webhook/set/oraculo" `
  -Headers @{ "apikey"="SUA_CHAVE"; "Content-Type"="application/json" } `
  -Body '{"url": "http://backend:8000/webhook/whatsapp", "enabled": true, "events": ["MESSAGES_UPSERT"]}'
```

### 4. Rodar migrations e popular dados
```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python seed_vendas.py
```

> O "número do bot" é o número do chip usado para escanear o QR code.

## Fluxo

1. Usuário manda mensagem no WhatsApp
2. Webhook recebe → verifica sessão → aplica rate limit
3. Se não autenticado: envia link de login
4. Se autenticado: enfileira task no Celery → worker processa com IA → responde

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
├── docker-compose.yml
└── .env
```
