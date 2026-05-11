<div align="center">

# Oráculo IA

**Sistema de Business Intelligence portuário com agente de IA conversacional**

[![Django](https://img.shields.io/badge/Django-6.0.5-092E20?style=flat-square&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16-000000?style=flat-square&logo=next.js&logoColor=white)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)

*Consulte dados operacionais portuários em linguagem natural. Sem SQL. Sem planilhas.*

</div>

---

## O que é

O **Oráculo** é uma plataforma de BI portuário que usa inteligência artificial para transformar perguntas em linguagem natural em análises de dados precisas.

No centro do sistema está o **ITA** — agente IA que entende perguntas sobre atracações, cargas, berços, produtividade e PLR, gera SQL automaticamente, executa no banco e devolve a resposta formatada com insights estatísticos e contexto geopolítico quando relevante.

**Exemplos de perguntas que o ITA responde:**

> *"Qual foi a produtividade média do berço 105 em janeiro de 2024?"*
> *"Quais cargas mais movimentaram no primeiro semestre? Faça um gráfico."*
> *"Por que a movimentação de fertilizantes caiu em 2025?"*
> *"Compare o PLR dos berços 101 e 108 nos últimos 12 meses."*

---

## Funcionalidades

| Módulo | Descrição |
|--------|-----------|
| **ITA Chat** | Agente conversacional com memória, gráficos interativos e análise estatística |
| **Dashboard** | Visão geral operacional com KPIs e acesso rápido |
| **Explorador de Dados** | Navegação por tabelas do banco com paginação e busca |
| **Base de Conhecimento** | CRUD para glossário, regras de negócio e contexto operacional |
| **Inteligência Externa** | Correlação automática de anomalias com eventos geopolíticos e notícias reais |

---

## Stack

| Camada | Tecnologia | Versão |
|--------|-----------|--------|
| Backend | Django + Django REST Framework | 6.0.5 |
| Banco de dados | PostgreSQL | 16 |
| Cache | Redis | 7 |
| LLM | DeepSeek via LangChain | deepseek-v4-flash |
| Frontend | Next.js + React + Tailwind CSS | 16 / 19 / 4 |
| Containers | Docker + Docker Compose | — |

---

## Arquitetura do Agente ITA

O agente processa cada pergunta em um pipeline de até **17 etapas**:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Pipeline do ITA                          │
├─────────────────────────────────────────────────────────────────┤
│  ETAPA 0    Detector de mudanças no banco (invalida cache)      │
│  ETAPA 1    Cache de Q&A  ──► resposta instantânea se match     │
│  ETAPA 2    Cache de SQL  ──► reutiliza queries anteriores      │
│  ETAPA 3    Preferências do usuário                             │
│  ETAPA 4-6  ║ Schema ║ Contexto portuário ║ Classificação ║     │
│             └──────── paralelizado ────────────────────┘        │
│  ETAPA 7    Detecção de ambiguidade                             │
│  ETAPA 8    Q&A aprendido (learning service)                    │
│  ETAPA 9    Geração de SQL                                      │
│  ETAPA 10   Validação do SQL (segurança + sintaxe)              │
│  ETAPA 11   Execução no banco                                   │
│  ETAPA 12   Validação do resultado                              │
│  ETAPA 13   Verificação cruzada (totalizações e médias)         │
│  ETAPA 14   Geração de gráfico (somente se solicitado)          │
│  ETAPA 14.7 Análise estatística avançada                        │
│             (tendência, anomalias, sazonalidade, forecast)      │
│  ETAPA 14.9 Inteligência Operacional Externa                    │
│             (notícias reais + correlação geopolítica)           │
│  ETAPA 15   Geração da resposta final                           │
│  ETAPA 16   Salvamento do aprendizado                           │
└─────────────────────────────────────────────────────────────────┘
```

### Skills do Agente

**Statistical Analysis Specialist** — roda em ETAPA 14.7
- Análise de qualidade dos dados
- Estatística descritiva (média, mediana, desvio padrão, quartis)
- Detecção de tendência (regressão linear, R²)
- Sazonalidade mensal/trimestral
- Detecção de anomalias (Z-Score + IQR)
- Forecast por regressão linear e suavização exponencial
- Correlação entre variáveis numéricas
- KPIs operacionais (throughput, produtividade, utilização)

**External Operational Intelligence** — roda em ETAPA 14.9
- Pesquisa de notícias reais via DuckDuckGo (links verificados)
- Correlação com eventos geopolíticos (guerras, sanções, crises)
- Análise de mercado por commodity (fertilizante, grãos, petróleo, minério)
- Comparação com outros portos (escopo local/nacional/global)
- Fatores climáticos (El Niño, tempestades, secas)
- Detecção de riscos operacionais externos
- Todas as hipóteses com nível de confiança explícito

---

## Estrutura do Repositório

```
oraculo-ia/
├── back/                         # Backend Django
│   ├── ai_agent/
│   │   ├── models.py             # Logs, aprendizado, glossário, regras, preferências
│   │   ├── views.py              # Endpoints REST (agente + knowledge CRUD)
│   │   ├── serializers.py        # Serializers DRF
│   │   ├── prompts/              # System prompt, answer prompt, SQL prompt
│   │   ├── services/             # agent_service, cache, schema, LLM, learning
│   │   └── tools/                # 30+ tools do pipeline do agente
│   ├── users/                    # Autenticação JWT
│   ├── core/                     # Settings, URLs, WSGI
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── front/                        # Frontend Next.js
│   ├── app/
│   │   ├── dashboard/
│   │   │   ├── ita/              # Chat com o agente ITA
│   │   │   ├── dados/            # Explorador de tabelas
│   │   │   └── conhecimento/     # CRUD da base de conhecimento
│   │   ├── api/                  # Proxies para o backend (autenticados)
│   │   ├── actions/              # Server Actions (login/logout)
│   │   └── login/
│   ├── components/
│   │   ├── chat/                 # Componentes de chat e gráficos
│   │   └── ui/                   # Componentes shadcn/ui
│   ├── Dockerfile
│   └── .env.example
├── sql/                          # Scripts de seed do banco
├── docker-compose.yml
└── README.md
```

---

## Início Rápido

### Pré-requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado e rodando
- Chave de API do [DeepSeek](https://platform.deepseek.com)

### 1. Clonar e configurar

```bash
git clone https://github.com/DaniloDalessandro/oraculo-ia.git
cd oraculo-ia

# Configurar variáveis do backend
cp back/.env.example back/.env
# Abra back/.env e preencha: DEEPSEEK_API_KEY=sk-...

# Frontend usa padrões automáticos com Docker
cp front/.env.example front/.env.local
```

### 2. Subir

```bash
docker compose up -d
```

### 3. Criar usuário administrador

```bash
docker exec -it oraculo-backend python manage.py createsuperuser
```

### 4. Acessar

| Serviço | URL |
|---------|-----|
| **Frontend** | http://localhost:3002 |
| Backend API | http://localhost:8001 |
| Admin Django | http://localhost:8001/admin/ |

---

## Desenvolvimento Local

### Backend

> Requer: Python 3.13+, PostgreSQL 16+, Redis 7+

```bash
cd back

python -m venv venv
source venv/bin/activate       # Linux/Mac
venv\Scripts\activate          # Windows

pip install -r requirements.txt

cp .env.example .env
# Configure DB_HOST=localhost e REDIS_URL=redis://localhost:6379/0

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 8001 --noreload
```

### Frontend

> Requer: Node.js 20+

```bash
cd front
npm install
cp .env.example .env.local
npx next dev --turbopack
```

Acesse em http://localhost:3000

---

## Variáveis de Ambiente

### `back/.env`

| Variável | Obrigatória | Descrição | Padrão |
|----------|:-----------:|-----------|--------|
| `DEEPSEEK_API_KEY` | ✅ | Chave da API DeepSeek | — |
| `DJANGO_SECRET_KEY` | ✅ prod | Chave secreta Django | insecure default |
| `DJANGO_DEBUG` | | Modo debug | `True` |
| `DJANGO_ALLOWED_HOSTS` | | Hosts permitidos | `localhost,127.0.0.1` |
| `DB_ENGINE` | | `postgresql` ou vazio (SQLite) | SQLite |
| `DB_NAME` | | Nome do banco | `oraculo` |
| `DB_USER` | | Usuário | `oraculo` |
| `DB_PASSWORD` | | Senha | `oraculo` |
| `DB_HOST` | | Host do banco | `postgres` |
| `DB_PORT` | | Porta | `5432` |
| `REDIS_URL` | | URL do Redis | `redis://localhost:6379/0` |
| `DJANGO_CORS_ALLOWED_ORIGINS` | | Origins CORS permitidas | `localhost:3000,3002` |
| `DEEPSEEK_MODEL` | | Modelo LLM | `deepseek-v4-flash` |
| `DEEPSEEK_TEMPERATURE` | | Temperatura | `0.1` |
| `AI_AGENT_LOG_LEVEL` | | Nível de log | `INFO` |

### `front/.env.local`

| Variável | Descrição | Padrão Docker |
|----------|-----------|:-------------:|
| `API_URL` | URL interna do backend (SSR/proxy) | `http://backend:8000` |
| `NEXT_PUBLIC_API_URL` | URL pública do backend (browser) | `http://localhost:8001` |

---

## API Reference

Todos os endpoints requerem `Authorization: Bearer <token>` (exceto login).

### Autenticação

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/api/auth/login/` | Login com email + senha → retorna JWT |
| `POST` | `/api/auth/refresh/` | Renovar access token |

### Agente ITA

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/ai-agent/ask/` | Enviar pergunta ao agente |
| `POST` | `/ai-agent/feedback/` | Registrar feedback (positivo/negativo) |
| `GET` | `/ai-agent/schema/` | Schema atual do banco |
| `GET` | `/ai-agent/schema/detail/` | Schema detalhado com colunas e tipos |
| `GET` | `/ai-agent/table-data/` | Dados de uma tabela com paginação |
| `POST` | `/ai-agent/refresh-schema/` | Invalidar cache do schema |

### Base de Conhecimento

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/ai-agent/knowledge/meta/` | Opções de categorias e tipos (choices) |
| `GET/POST` | `/ai-agent/knowledge/` | Listar / criar conhecimento |
| `GET/PATCH/DELETE` | `/ai-agent/knowledge/<id>/` | Detalhar / editar / deletar |
| `GET/POST` | `/ai-agent/glossary/` | Listar / criar termo do glossário |
| `GET/PATCH/DELETE` | `/ai-agent/glossary/<id>/` | Detalhar / editar / deletar |
| `GET/POST` | `/ai-agent/rules/` | Listar / criar regra de negócio |
| `GET/PATCH/DELETE` | `/ai-agent/rules/<id>/` | Detalhar / editar / deletar |

### Exemplo de uso

```bash
# Login
curl -X POST http://localhost:8001/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@exemplo.com", "password": "senha"}'

# Pergunta ao agente
curl -X POST http://localhost:8001/ai-agent/ask/ \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"question": "Qual foi a carga mais movimentada no berço 101 em 2024?"}'
```

---

## Comandos Úteis

```bash
# Logs em tempo real
docker compose logs -f backend
docker compose logs -f frontend

# Rebuild sem cache
docker compose build --no-cache && docker compose up -d

# Migrations
docker exec -it oraculo-backend python manage.py migrate

# Testes
docker exec -it oraculo-backend python manage.py test ai_agent

# Seed da base de conhecimento
docker exec -it oraculo-backend python manage.py seed_port_knowledge

# Parar tudo
docker compose down

# Parar e apagar banco de dados
docker compose down -v
```

---

## Licença

Uso interno — Porto de Itaquí.
