# Fellow BOT — Testing Guide

> **Purpose:** How to test the entire system — automated suite, manual checks, and pre-deployment verification.
>
> **Estimated Time:** Automated suite ~2 min; full manual walkthrough ~45 min
>
> **Tester:** Developer / QA

---

## Prerequisites

- [ ] PostgreSQL running with `pgvector` extension installed
- [ ] Ollama server accessible (remote or local) with `nomic-embed-text` and `llama3.2`
- [ ] Python 3.10+ with dependencies installed (`pip install -r requirements.txt`)
- [ ] Node.js 18+ (for admin dashboard build)
- [ ] `.env` file configured (copy from `.env.example`, fill real values)
- [ ] Database migration applied (pgvector extension + initial schema)
- [ ] Server running: `python -m uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload`

---

## Automated Integration Tests

### Run the full suite

```bash
python -X utf8 scripts/run_tests.py
```

This runs **41 assertions** across all modules in sequence. Expected output:

```
============================================================
  TOTAL:  41 passed    0 failed
  STATUS: ALL TESTS PASSED
============================================================
```

### What the automated tests cover

| # | Section | Assertions |
|---|---|---|
| 1 | Health check | Server healthy |
| 2 | Auth — Register | User created, JWT returned |
| 3 | Auth — Login | Tokens issued |
| 4 | Auth — Me | Profile returned with correct email |
| 5 | Organizations | Create org, get org, list orgs |
| 6 | Subscriptions | Subscription assigned to org |
| 7 | Token balance | Balance readable for org |
| 8 | AI Providers | Create Ollama provider, list providers |
| 9 | Chatbots | Create chatbot, set persona, set theme |
| 10 | Chatbot prompts | Create tenant prompt layer |
| 11 | Knowledge Base | Create KB, list KBs |
| 12 | Q&A Pairs | Create pair, list pairs |
| 13 | Training data upload | Upload Excel file, verify inserted count |
| 14 | Sync embeddings | POST sync-embeddings returns synced count |
| 15 | RAG search | Semantic search returns relevant result |
| 16 | Chat widget (public) | Create session, get history |
| 17 | Live RAG chat | 5 real questions answered with correct KB context |

### Live RAG chat assertions

The test asks 5 real questions about ICT Bangladesh and checks the answers contain correct factual keywords:

```
Q: Who is the founder of ICT Bangladesh?
A: (must mention "Israfeel Masum")

Q: How much does the AI Engineer course cost?
A: (must mention a price)

Q: How long is the AI Engineer course?
A: (must mention sessions/months/weeks)

Q: How do I enroll in ICT Bangladesh?
A: (must mention enrollment/website/contact)

Q: What programming language is taught?
A: (must mention Python or a language name)
```

---

## Manual Testing Checklist

### A. Server Startup

- [ ] `http://localhost:9000/health` → `{"status": "healthy"}`
- [ ] `http://localhost:9000/docs` → Swagger UI loads with all routes
- [ ] `http://localhost:9000/admin` → Admin Dashboard login page
- [ ] `http://localhost:9000/` → Chat widget loads

---

### B. Admin Dashboard Login

1. Open `http://localhost:9000/admin`
2. Enter valid email and password
3. Click Login

- [ ] Redirects to Overview page
- [ ] Sidebar navigation visible
- [ ] Overview stats cards show (chatbots, conversations, KB docs, tokens)

---

### C. Create Chatbot Wizard

1. Click **🤖 Create Chatbot** on Overview
2. Fill in Step 1 (Basics): name, description
3. Fill in Step 2 (Persona): persona name, greeting
4. Review Step 3
5. Confirm Step 4 done

- [ ] Wizard opens as modal
- [ ] All 4 steps navigate correctly
- [ ] Chatbot created successfully (shown in Step 4)
- [ ] Chatbot appears in Overview after closing wizard

---

### D. Settings — Persona & Chat

1. Go to **Settings** → Persona & Chat tab
2. Edit Persona Name, Greeting Message, Default Language, Personality
3. Add/edit System Prompt (multi-line textarea)
4. Click **Save Persona**

- [ ] All fields pre-populated with current values
- [ ] System Prompt textarea visible (10 rows)
- [ ] Save sends PATCH to persona endpoint — no HTTP 405 error
- [ ] System Prompt saved as tenant prompt layer (verify in `/api/v1/.../prompts` endpoint)
- [ ] Success toast shown

---

### E. Settings — Theme

1. Go to **Settings** → Theme tab
2. Change primary color, widget position
3. Click **Save Theme**

- [ ] Save sends PATCH to theme endpoint — no HTTP 405 error
- [ ] Success toast shown

---

### F. Knowledge Base — Q&A Management

1. Go to **Knowledge** in sidebar
2. Select (or create) a knowledge base
3. Click **+ Add Q&A**
4. Fill in question, answer, category, relevant questions
5. Save

- [ ] Q&A pair appears in list
- [ ] Embedding status shows as indexed (not pending)
- [ ] Ask the same question in the chat widget → bot answers from KB context

---

### G. Training Data Upload

1. Prepare an Excel file with `question` and `answer` columns (minimum 3 rows)
2. Go to Knowledge → select KB → click **Upload Training Data**
3. Select the file, leave "Clear existing" unchecked
4. Upload

- [ ] Upload completes with `inserted: N` count
- [ ] Pairs appear in Q&A list
- [ ] New pairs searchable in chat immediately

---

### H. Document Upload

1. Prepare a PDF or DOCX file (any content)
2. Go to Knowledge → select KB → click **Upload Document**
3. Select file and upload

- [ ] Document appears in documents list
- [ ] Status eventually shows `indexed` (may take a few seconds)

---

### I. Sync Embeddings

1. Manually add a Q&A pair via API without triggering embedding (or just verify the endpoint works)
2. Go to Knowledge → click **Sync Embeddings**

- [ ] Returns `{"synced": N, "total_unembedded": M}`
- [ ] If `M > 0`, synced should equal M (or up to 500)

---

### J. Chat Widget — Core Functionality

1. Open `http://localhost:9000/`
2. The chat widget should be visible
3. Verify greeting message appears automatically on load

- [ ] Greeting message shown (from persona config)
- [ ] Greeting renders markdown (bold, links, etc.)
- [ ] Type a question → bot responds with streaming text (no full-page reload)
- [ ] Response streams token by token (visible typewriter effect)

---

### K. Chat Widget — Language Detection

1. Type a message in Bengali: `আইসিটি বাংলাদেশ এর কোর্স ফি কত?`
2. Observe the response

- [ ] Bot responds entirely in Bengali (not English)
- [ ] Subsequent messages in the same session also receive Bengali responses
3. Type an English message
- [ ] Bot switches back to English

---

### L. Chat Widget — Link Rendering

1. Ask a question that includes a URL in the answer (e.g., "How do I enroll?")
2. Check the response

- [ ] URLs in bot responses are rendered as clickable hyperlinks
- [ ] Links open in a new tab (`target="_blank"`)
- [ ] Entity names like "ICT Bangladesh" are auto-linked to the website
- [ ] "Israfeel Masum" is auto-linked

---

### M. Chat Widget — Suggestion Chips

1. After a bot response, look below the message for suggestion buttons

- [ ] Up to 3 suggestion chips appear (related questions from the KB)
- [ ] Clicking a chip sends that question automatically

---

### N. Conversation History

1. Start a chat session and send 3+ messages
2. Close and reopen the widget (or new session)
3. Check via API: `GET /api/v1/chat/sessions/{id}/messages`

- [ ] All messages persisted with correct role (user/assistant)
- [ ] Within a session, bot remembers earlier context (not treated as new)

---

### O. Escalation Flow

1. In the chat widget, type: `I want to talk to a human agent`
2. Go to **Conversations** → filter by **Escalated**

- [ ] Escalated conversation appears
- [ ] Click it → full message thread visible
- [ ] Type and send an agent reply
- [ ] Reply appears in the conversation

---

### P. Super Admin — Tenant Management

1. Log in as a super admin user
2. Go to **Super Admin** in sidebar

- [ ] All organizations listed with status, token balance
- [ ] **⚙ Settings** button opens tenant settings panel
- [ ] **🔋 Tokens** button opens top-up modal
- [ ] Top-up modal shows preset buttons (100K / 500K / 1M)
- [ ] After top-up, balance updates in the panel
- [ ] **Suspend** changes org status to suspended
- [ ] **Activate** restores it

---

### Q. API Security

```bash
# Should return 401 (no token)
curl http://localhost:9000/api/v1/auth/me
# Expected: {"detail": "Not authenticated"}

# Should return 401 (bad token)
curl http://localhost:9000/api/v1/auth/me \
  -H "Authorization: Bearer fake.token.here"
# Expected: {"detail": "Could not validate credentials"}

# Should return 403 (correct token, wrong org)
# Try accessing another org's resources with a different org's token
```

- [ ] All protected endpoints return 401 without valid token
- [ ] Expired tokens rejected with 401
- [ ] Cross-org access returns 403

---

## Test Results Summary

| # | Area | Result | Notes |
|---|---|--------|-------|
| Auto | Automated suite (41 assertions) | | `python -X utf8 scripts/run_tests.py` |
| A | Server startup | | |
| B | Admin login | | |
| C | Create chatbot wizard | | |
| D | Settings — Persona & Chat | | |
| E | Settings — Theme | | |
| F | Knowledge Base — Q&A | | |
| G | Training data upload | | |
| H | Document upload | | |
| I | Sync embeddings | | |
| J | Chat widget — core | | |
| K | Language detection (Bengali) | | |
| L | Link rendering | | |
| M | Suggestion chips | | |
| N | Conversation history | | |
| O | Escalation flow | | |
| P | Super admin — tenant management | | |
| Q | API security | | |

---

## Common Issues & Fixes

### Chat responds in English despite Bengali input

**Cause:** Language detection not triggering, or LLM ignoring the instruction.

**Fix:** Check that the message is at least 10 characters of Bengali text (very short messages may not be confidently detected). The LANGUAGE LAW injection only fires when `detected_lang != "en"`.

---

### New Q&A pairs not showing up in chat responses

**Cause:** Embedding was not created for the new pair.

**Fix:** Click **Sync Embeddings** on the knowledge base in the admin UI, or call:
```bash
POST /api/v1/organizations/{org_id}/knowledge-bases/{kb_id}/sync-embeddings
```

---

### Settings save returns HTTP 405

**Cause:** Using a method (PUT vs PATCH) not supported by the endpoint.

**Fix:** The persona and theme endpoints now accept both PUT and PATCH. If still failing, check the request method in the browser dev tools Network tab.

---

### Widget shows no greeting message on load

**Cause:** Persona `greeting_message` is empty, or the chatbot config failed to load.

**Fix:** Set the Greeting Message in Settings → Persona & Chat → save. Then reload the widget page.

---

### RAG search returns irrelevant results

**Cause:** KB has very few Q&A pairs, or the question phrasing is far from any trained Q&A.

**Fix:** Add more Q&A pairs with alternate phrasings in the **Relevant Questions** field. The more varied phrasings you include, the better semantic coverage.

---

### Ollama connection error

**Cause:** `OLLAMA_BASE_URL` in `.env` points to an unreachable server.

**Fix:** Verify the Ollama server is running and accessible. Test with:
```bash
curl https://your-ollama-server/api/tags
# Should return list of available models
```

---

## Pre-Deployment Checklist

Before deploying to production:

- [ ] All 41 automated tests pass
- [ ] Admin dashboard built: `cd admin-dashboard && npm run build`
- [ ] `DEBUG=false` in `.env`
- [ ] `SECRET_KEY` is a strong random string (32+ chars)
- [ ] `ALLOWED_ORIGINS` contains only production domains
- [ ] Ollama server URL is the production endpoint
- [ ] PostgreSQL `pgvector` extension installed on production DB
- [ ] Migrations applied to production DB
- [ ] SMTP configured for escalation alerts
- [ ] SSL/TLS configured on reverse proxy
- [ ] Health check endpoint responding: `GET /health`
