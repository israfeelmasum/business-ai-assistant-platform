# 🤖 Business AI Assistant Platform

> **Production-ready, multi-tenant AI chatbot SaaS** — embed a smart assistant on any website in minutes. Powered by open-source LLMs (Ollama/llama3.2), semantic RAG search (pgvector), and a full React admin dashboard.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?logo=postgresql)](https://github.com/pgvector/pgvector)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://reactjs.org)
[![Ollama](https://img.shields.io/badge/Ollama-llama3.2-000000)](https://ollama.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 📸 Screenshots

<table>
  <tr>
    <td align="center"><b>Dashboard Overview</b></td>
    <td align="center"><b>Knowledge Base Manager</b></td>
  </tr>
  <tr>
    <td><img src="screenshots/01_dashboard_overview.png" alt="Dashboard Overview" width="100%"/></td>
    <td><img src="screenshots/02_knowledge_base.png" alt="Knowledge Base" width="100%"/></td>
  </tr>
  <tr>
    <td align="center"><b>Embeddable Chat Widget</b></td>
    <td align="center"><b>Persona & Settings</b></td>
  </tr>
  <tr>
    <td><img src="screenshots/03_chat_widget.png" alt="Chat Widget" width="100%"/></td>
    <td><img src="screenshots/04_settings_persona.png" alt="Settings" width="100%"/></td>
  </tr>
  <tr>
    <td align="center" colspan="2"><b>Super Admin — Tenant Management</b></td>
  </tr>
  <tr>
    <td colspan="2"><img src="screenshots/05_super_admin.png" alt="Super Admin" width="100%"/></td>
  </tr>
</table>

---

## ✨ Features

| Feature | Description |
|---|---|
| 🏢 **Multi-tenant** | Each organization gets isolated chatbots, knowledge bases, and analytics |
| 🧠 **RAG-powered answers** | Semantic search with pgvector HNSW index across multiple knowledge bases |
| 📚 **Bulk training data** | Upload Excel/CSV to train your bot in seconds |
| 🌐 **Multi-language** | Auto-detects user language (Bengali, English, 80+ more) and responds in kind |
| ⚡ **Streaming responses** | Server-Sent Events (SSE) for real-time token-by-token streaming |
| 🎨 **Embeddable widget** | Single `<script>` tag — drop it on any website, React app, or WordPress |
| 🔐 **JWT authentication** | Secure login/refresh, role-based access (super_admin, org_admin) |
| 💬 **Human escalation** | Users can request a live agent; admins reply from the dashboard |
| 📊 **Analytics** | Conversation volume, RAG hit rates, language breakdown |
| 🔋 **Token billing** | Per-org usage credits with top-up management |
| 🤖 **Create Chatbot Wizard** | 4-step guided setup from the Overview dashboard |

---

## 🏗️ Architecture

```
Browser
  ├── Chat Widget (/)         → Vanilla JS + marked.js, SSE streaming
  └── Admin Dashboard (/admin) → React 18 + Vite + Tailwind CSS

FastAPI (Python 3.10)
  ├── JWT auth          ├── Organizations    ├── Token billing
  ├── Chatbots          ├── Prompt layers    ├── Knowledge bases
  ├── RAG pipeline      ├── Chat sessions    └── Analytics

PostgreSQL 15 + pgvector
  └── HNSW cosine index — 768-dim embeddings

Ollama (self-hosted or remote)
  ├── nomic-embed-text  →  768-dim embeddings for semantic search
  └── llama3.2:latest   →  3B parameter chat LLM
```

### Multi-tenant data model

```
Organization (tenant)
  └── Chatbot
        ├── Persona + Theme + Prompt Layers
        └── Knowledge Base(s)
              ├── Q&A Pairs  (embedded for semantic search)
              └── Documents  (PDF/DOCX/TXT → chunked + embedded)
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL 15+ with [`pgvector`](https://github.com/pgvector/pgvector) extension
- [Ollama](https://ollama.com) (local or remote)
- Node.js 18+

### 1. Clone & configure

```bash
git clone https://github.com/israfeelmasum/business-ai-assistant-platform.git
cd business-ai-assistant-platform

cp .env.example .env
# Edit .env — set DATABASE_URL, OLLAMA_BASE_URL, SECRET_KEY
```

### 2. Install & migrate

```bash
# Python dependencies
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Database
psql -U postgres -c "CREATE DATABASE ai_chatbot_db;"
psql -U postgres -d ai_chatbot_db -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -U postgres -d ai_chatbot_db -f migrations/001_initial.sql
```

### 3. Build dashboard & start server

```bash
cd admin-dashboard && npm install && npm run build && cd ..
uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload
```

### 4. Open the platform

| URL | What you get |
|---|---|
| `http://localhost:9000/` | Embeddable chat widget |
| `http://localhost:9000/admin` | Admin Dashboard |
| `http://localhost:9000/docs` | Interactive API docs (Swagger) |
| `http://localhost:9000/health` | Health check |

### 5. Create your first account

```bash
curl -X POST http://localhost:9000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@yourdomain.com", "password": "YourPassword1!", "full_name": "Admin"}'
```

Then open `/admin` and follow the **Create Chatbot Wizard** to set up your first chatbot in 4 steps.

---

## 📦 Embed on Your Website

### Script tag (any HTML page)

```html
<script
  src="https://your-server.com/chatbot-widget.js"
  data-org-id="YOUR_ORG_ID"
  data-chatbot-id="YOUR_CHATBOT_ID"
  data-api-url="https://your-server.com/api/v1"
></script>
```

Widget is fully configured from your Admin Dashboard settings — no code changes needed for persona, colors, or greeting.

### React component

See [`INTEGRATION_GUIDE.md`](INTEGRATION_GUIDE.md) for a full React SSE streaming component example.

---

## 🧠 Training Your Bot

### Option 1: Upload Excel/CSV (fastest)

Create a spreadsheet with `question` and `answer` columns:

| question | answer | category | relevant questions |
|---|---|---|---|
| What do you offer? | We offer X, Y, Z services... | General | What are your services / What can you do |
| How much does it cost? | Pricing starts at... | Pricing | Price / Cost / Fee |

Upload via **Admin Dashboard → Knowledge → Upload Training Data**, or via API:

```bash
curl -X POST "http://localhost:9000/api/v1/organizations/{org_id}/knowledge-bases/{kb_id}/training-data/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@training_data.xlsx" \
  -F "clear_existing=false"
```

### Option 2: Add Q&A pairs directly

Use the admin dashboard to add individual Q&A pairs with categories and related questions.

### Option 3: Upload documents

Upload PDF, DOCX, or TXT files — they're automatically chunked and embedded for semantic search.

---

## 🌐 Language Support

The bot **automatically detects** the user's language on every message and responds in the same language. No configuration needed.

```
User: "আপনার সার্ভিসের মূল্য কত?"  →  Bot responds in Bengali
User: "What is your price?"          →  Bot responds in English
```

Supports 80+ languages via `langdetect`. The language setting persists per conversation session.

---

## ⚙️ Configuration

Key environment variables (see `.env.example` for full list):

```bash
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/ai_chatbot_db
OLLAMA_BASE_URL=http://localhost:11434     # or remote Ollama server
OLLAMA_EMBEDDING_MODEL=nomic-embed-text   # 768-dim
OLLAMA_CHAT_MODEL=llama3.2:latest
SECRET_KEY=your-random-32-char-secret
EMBEDDING_DIMENSION=768                   # must match pgvector column
ALLOWED_ORIGINS=https://yourdomain.com
```

> **OpenAI / Gemini:** Set `OPENAI_API_KEY` or `GOOGLE_API_KEY` and configure an AI provider in the admin dashboard to use cloud models instead of Ollama.

---

## 📁 Project Structure

```
├── app/
│   ├── main.py                  FastAPI app entry point
│   └── modules/
│       ├── auth/                JWT auth, user management
│       ├── organizations/       Tenant management
│       ├── tokens/              Usage credit ledger
│       ├── ai_providers/        Multi-provider AI key management
│       ├── chatbots/            Chatbot config, persona, themes, prompt layers
│       ├── knowledge/           KB, Q&A pairs, documents, RAG pipeline
│       ├── chat/                SSE streaming, conversation history
│       ├── escalation/          Human handoff
│       └── analytics/           Usage metrics and reporting
├── frontend/
│   └── index.html               Embeddable chat widget
├── admin-dashboard/             React 18 + Vite + Tailwind admin panel
├── scripts/
│   ├── run_tests.py             Integration test suite
│   └── seed_dev.py              Dev environment reference helper
├── migrations/                  SQL migration files
├── .env.example                 Environment variable template
└── requirements.txt
```

---

## 🧪 Tests

```bash
# Set up environment variables for your local test accounts
export TEST_SA_EMAIL=superadmin@example.com
export TEST_SA_PASSWORD=YourPassword1!
export TEST_ORG_EMAIL=admin@yourorg.com
export TEST_ORG_PASSWORD=YourPassword2!
export TEST_ORG_ID=your-org-uuid
export TEST_CB_ID=your-chatbot-uuid
export TEST_KB_ID=your-kb-uuid

python scripts/run_tests.py
```

The test suite covers: auth, organizations, token billing, AI providers, chatbots, knowledge base CRUD, bulk upload, RAG search, chat sessions, and live streaming responses.

---

## 🤝 AI Provider Support

| Provider | Chat | Embeddings | Notes |
|---|---|---|---|
| **Ollama** (default) | ✅ | ✅ | Self-hosted, `nomic-embed-text` + `llama3.2` |
| **OpenAI** | ✅ | ✅ | `gpt-4o`, `text-embedding-3-small` (1536-dim) |
| **Google Gemini** | ✅ | ❌ | Falls back to Ollama for embeddings |

> If switching to OpenAI embeddings (1536-dim), update `EMBEDDING_DIMENSION=1536` and re-run the migration with `vector(1536)`.

---

## 🔒 Security

- All API endpoints protected by JWT Bearer tokens
- Passwords hashed with bcrypt
- Per-organization data isolation (tenants cannot access each other's data)
- CORS restricted to configured origins
- Sensitive keys stored encrypted in the database

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 📚 Documentation

- [`INTEGRATION_GUIDE.md`](INTEGRATION_GUIDE.md) — User guide: embed widget, train bot, manage knowledge base
- [`TESTING_GUIDE.md`](TESTING_GUIDE.md) — Manual testing checklist and pre-deployment verification
- `/docs` — Interactive Swagger API documentation (when server is running)
