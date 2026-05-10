# Oráculo

Sistema de Business Intelligence portuário com agente de IA conversacional. Permite consultar dados operacionais do Porto de Itaguaí em linguagem natural.

## Visão Geral

- **ITA** — agente IA que responde perguntas sobre atracações, cargas, berços e produtividade
- **Dashboard** — visão geral dos dados operacionais
- **Dados** — explorador de tabelas do banco
- **Conhecimento** — CRUD da base de conhecimento do agente (glossário, regras de negócio, contexto operacional)

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Django 6.0.5 + Django REST Framework |
| Banco | PostgreSQL 16 |
| Cache | Redis 7 |
| IA | LangChain + DeepSeek API |
| Frontend | Next.js 16 + React 19 + Tailwind CSS 4 |
| Containers | Docker + Docker Compose |

---

## Estrutura do Projeto

```
oraculo/
├── back/                    # Backend Django
│   ├── ai_agent/            # App do agente IA
│   │   ├── models.py        # Modelos (logs, conhecimento, glossário, regras)
│   │   ├── views.py         # Endpoints REST
│   │   ├── serializers.py   # Serializers DRF
│   │   ├── services/        # Serviços (agente, cache, schema, LLM)
│   │   ├── tools/           # Tools do agente (SQL, classificador, estatística)
│   │   └── prompts/         # Prompts do LLM
│   ├── users/               # App de autenticação JWT
│   ├── core/                # Settings, URLs, WSGI
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env                 # Variáveis de ambiente (não commitado)
│   └── .env.example         # Template de variáveis
├── front/                   # Frontend Next.js
│   ├── app/
│   │   ├── dashboard/       # Páginas do dashboard
│   │   │   ├── ita/         # Chat com o agente
│   │   │   ├── dados/       # Explorador de dados
│   │   │   └── conhecimento/ # CRUD da base de conhecimento
│   │   ├── api/             # Routes proxy para o backend
│   │   ├── actions/         # Server Actions (auth)
│   │   └── login/           # Página de login
│   ├── components/          # Componentes React (sidebar, chat, UI)
│   ├── Dockerfile
│   ├── .env.local           # Variáveis de ambiente (não commitado)
│   └── .env.example         # Template de variáveis
├── sql/                     # Scripts SQL de seed
├── docker-compose.yml
└── README.md
```

---

## Rodando com Docker (recomendado)

### Pré-requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado e rodando
- Chave de API do DeepSeek ([platform.deepseek.com](https://platform.deepseek.com))

### 1. Configurar variáveis de ambiente

```bash
# Backend
cp back/.env.example back/.env
# Edite back/.env e preencha DEEPSEEK_API_KEY

# Frontend (opcional — os padrões já funcionam com Docker)
cp front/.env.example front/.env.local
```

### 2. Subir os containers

```bash
docker compose up -d
```

### 3. Acessar

| Serviço | URL |
|---------|-----|
| Frontend | http://localhost:3002 |
| Backend API | http://localhost:8001 |
| API Docs (admin) | http://localhost:8001/admin/ |

### 4. Criar usuário admin (primeiro acesso)

```bash
docker exec -it oraculo-backend python manage.py createsuperuser
```

---

## Rodando em Desenvolvimento Local

### Backend

**Pré-requisitos:** Python 3.13+, PostgreSQL 16+, Redis 7+

```bash
cd back

# Criar e ativar virtualenv
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# Instalar dependências
pip install -r requirements.txt

# Configurar .env
cp .env.example .env
# Edite .env com suas configurações locais

# Aplicar migrations
python manage.py migrate

# Criar superusuário
python manage.py createsuperuser

# Rodar servidor (porta 8001 para não conflitar com Docker)
python manage.py runserver 8001 --noreload
```

### Frontend

**Pré-requisitos:** Node.js 20+

```bash
cd front

# Instalar dependências
npm install

# Configurar .env
cp .env.example .env.local
# Edite NEXT_PUBLIC_API_URL se necessário

# Rodar servidor de desenvolvimento
npx next dev --turbopack
```

Acesse em http://localhost:3000

---

## Variáveis de Ambiente

### Backend (`back/.env`)

| Variável | Obrigatória | Descrição | Padrão |
|----------|------------|-----------|--------|
| `DJANGO_SECRET_KEY` | Sim (prod) | Chave secreta do Django | insecure default |
| `DJANGO_DEBUG` | Não | Modo debug | `True` |
| `DJANGO_ALLOWED_HOSTS` | Não | Hosts permitidos | `localhost,127.0.0.1` |
| `DB_ENGINE` | Não | `postgresql` ou vazio (SQLite) | SQLite |
| `DB_NAME` | Não | Nome do banco | `oraculo` |
| `DB_USER` | Não | Usuário do banco | `oraculo` |
| `DB_PASSWORD` | Não | Senha do banco | `oraculo` |
| `DB_HOST` | Não | Host do banco | `postgres` |
| `DB_PORT` | Não | Porta do banco | `5432` |
| `REDIS_URL` | Não | URL do Redis | `redis://localhost:6379/0` |
| `DJANGO_CORS_ALLOWED_ORIGINS` | Não | Origins permitidas pelo CORS | `http://localhost:3000,3002` |
| `DEEPSEEK_API_KEY` | **Sim** | Chave da API DeepSeek | — |
| `DEEPSEEK_MODEL` | Não | Modelo DeepSeek | `deepseek-v4-flash` |
| `DEEPSEEK_TEMPERATURE` | Não | Temperatura do LLM | `0.1` |
| `AI_AGENT_LOG_LEVEL` | Não | Nível de log do agente | `INFO` |

### Frontend (`front/.env.local`)

| Variável | Descrição | Padrão Docker |
|----------|-----------|--------------|
| `API_URL` | URL interna do backend (SSR) | `http://backend:8000` |
| `NEXT_PUBLIC_API_URL` | URL pública do backend (browser) | `http://localhost:8001` |

---

## Endpoints da API

### Autenticação
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/api/auth/login/` | Login (retorna JWT) |
| `POST` | `/api/auth/refresh/` | Renovar token |

### Agente IA
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/ai-agent/ask/` | Fazer pergunta ao agente |
| `POST` | `/ai-agent/feedback/` | Registrar feedback |
| `GET` | `/ai-agent/schema/` | Ver schema do banco |
| `POST` | `/ai-agent/refresh-schema/` | Invalidar cache do schema |

### Base de Conhecimento
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET/POST` | `/ai-agent/knowledge/` | Listar/criar conhecimento |
| `GET/PATCH/DELETE` | `/ai-agent/knowledge/<id>/` | Detalhar/editar/deletar |
| `GET/POST` | `/ai-agent/glossary/` | Listar/criar glossário |
| `GET/PATCH/DELETE` | `/ai-agent/glossary/<id>/` | Detalhar/editar/deletar |
| `GET/POST` | `/ai-agent/rules/` | Listar/criar regras de negócio |
| `GET/PATCH/DELETE` | `/ai-agent/rules/<id>/` | Detalhar/editar/deletar |

Todos os endpoints requerem autenticação JWT: `Authorization: Bearer <token>`

---

## Comandos Úteis

```bash
# Ver logs dos containers
docker compose logs -f backend
docker compose logs -f frontend

# Rebuild completo (sem cache)
docker compose build --no-cache && docker compose up -d

# Rodar migrations dentro do container
docker exec -it oraculo-backend python manage.py migrate

# Rodar testes
docker exec -it oraculo-backend python manage.py test ai_agent

# Parar tudo
docker compose down

# Parar e remover volumes (apaga banco)
docker compose down -v
```

---

## Arquitetura do Agente IA

O agente processa cada pergunta em até 16 etapas sequenciais:

```
ETAPA 0  — Detector de mudanças no banco (invalida cache se necessário)
ETAPA 1  — Busca de Q&A em cache (resposta instantânea se houver match)
ETAPA 2  — Busca de SQL em cache (reutiliza queries anteriores)
ETAPA 3  — Recuperação de preferências do usuário
ETAPA 4-6 — Paralelo: schema + contexto portuário + classificação da pergunta
ETAPA 7  — Detecção de ambiguidade (pede esclarecimento se necessário)
ETAPA 8  — Verificação de Q&A aprendido
ETAPA 9  — Geração de SQL
ETAPA 10 — Validação do SQL
ETAPA 11 — Execução do SQL
ETAPA 12 — Validação do resultado
ETAPA 13 — Verificação cruzada (apenas totalizações e médias)
ETAPA 14 — Detecção de gráfico (apenas se usuário pedir explicitamente)
ETAPA 14.7 — Análise estatística (tendência, anomalias, sazonalidade)
ETAPA 15 — Geração da resposta final
ETAPA 16 — Salvamento do aprendizado
```

---

## Licença

Uso interno — Porto de Itaguaí.
