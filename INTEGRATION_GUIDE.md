# Fellow BOT — User & Integration Guide

This guide covers everything a tenant admin (organization owner) needs to set up, configure, and embed the Fellow BOT chatbot on their website.

---

## Table of Contents

1. [Getting Access](#1-getting-access)
2. [Admin Dashboard Overview](#2-admin-dashboard-overview)
3. [Create Your First Chatbot](#3-create-your-first-chatbot)
4. [Configure Persona & Settings](#4-configure-persona--settings)
5. [Build Your Knowledge Base](#5-build-your-knowledge-base)
6. [Upload Training Data (Excel/CSV)](#6-upload-training-data-excelcsv)
7. [Embed the Chat Widget](#7-embed-the-chat-widget)
8. [Language Support](#8-language-support)
9. [Monitor Conversations](#9-monitor-conversations)
10. [Human Escalation](#10-human-escalation)
11. [Token Usage & Billing](#11-token-usage--billing)
12. [Super Admin — Managing Tenants](#12-super-admin--managing-tenants)

---

## 1. Getting Access

1. Your Super Admin creates an organization account for you and provides:
   - Admin Dashboard URL: `https://your-server.com/admin`
   - Your login email and password
2. Open the dashboard URL in your browser
3. Log in with your credentials
4. You are taken directly to the **Overview** page

> **First login?** Change your password from the Settings page after logging in.

---

## 2. Admin Dashboard Overview

The sidebar navigation contains:

| Page | Purpose |
|---|---|
| **Overview** | Stats summary, quick actions, create chatbot wizard |
| **Knowledge** | Manage knowledge bases, Q&A pairs, documents |
| **Conversations** | View all chat history and escalated conversations |
| **Analytics** | Message volume, RAG hit rates, language breakdown |
| **Settings** | Persona, theme, system prompt, integrations, API config |
| **Super Admin** | Tenant management (super admin role only) |

The **Overview** page shows:
- Active chatbots count
- Total conversations
- Knowledge base document count
- Token balance

Quick action buttons at the top let you jump directly to **Create Chatbot**, **Add Knowledge**, or **Settings**.

---

## 3. Create Your First Chatbot

### Using the Wizard (Recommended)

1. Go to **Overview**
2. Click **🤖 Create Chatbot**
3. The 4-step wizard opens:

**Step 1 — Basics**
- **Name** — Internal reference name (e.g., "ICT Bangladesh Bot")
- **Description** — What this chatbot does
- **Slug** — Auto-generated URL-friendly ID (e.g., `ict-bangladesh-bot`)

**Step 2 — Persona**
- **Persona Name** — The name the bot introduces itself as (e.g., "Aisha")
- **Greeting Message** — First message shown when a user opens the chat
- **Language** — Default response language
- **Personality** — Tone descriptor (e.g., "friendly, professional, helpful")

**Step 3 — Review**
- Review all settings before creating

**Step 4 — Done**
- Chatbot created! The chatbot ID is shown — you'll need it for embedding.

### Manual Creation via API

```bash
POST /api/v1/organizations/{org_id}/chatbots
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "ICT Bangladesh Bot",
  "description": "Answers questions about ICT Bangladesh courses",
  "slug": "ictbangladesh"
}
```

---

## 4. Configure Persona & Settings

Go to **Settings** in the sidebar. Settings are organized in tabs:

### Persona & Chat Tab

| Field | Description |
|---|---|
| Persona Name | Name the bot uses (shown in chat header) |
| Default Language | `en`, `bn`, or other language code |
| Personality | Tone description injected into the prompt |
| Greeting Message | Opening message shown at session start |
| System Prompt | Business-specific instructions for the AI (see below) |

**System Prompt** is the most important field. Use it to:
- Describe your business and what the bot should know
- Set rules (e.g., "Always recommend contacting sales for pricing above 50,000 BDT")
- Define escalation behavior (e.g., "If you don't know the answer, offer to connect with a human agent")
- Restrict scope (e.g., "Only answer questions about ICT Bangladesh courses and services")

Example system prompt:
```
You are a helpful assistant for ICT Bangladesh, a technology education company in Dhaka.
You help prospective students learn about our courses, enrollment process, fees, and schedule.
Always be friendly and professional. If a user asks about topics outside ICT Bangladesh, 
politely redirect them. For complex enrollment questions, suggest they visit 
ictbangladesh.com.bd or contact our support team.
```

Click **Save Persona** to apply. Changes take effect immediately on the next chat session.

### Theme Tab

| Field | Description |
|---|---|
| Primary Color | Chat bubble and header color (hex) |
| Secondary Color | Button and accent color |
| Bot Avatar URL | URL to bot profile image |
| Widget Position | `bottom-right` or `bottom-left` |
| Chat Title | Header text shown in the widget |
| Welcome Message | Subtitle text under the chat title |

### Integration Tab

Shows your chatbot's embed code (auto-generated with your org and chatbot IDs).

---

## 5. Build Your Knowledge Base

The knowledge base is what the bot searches when answering questions. It supports multiple knowledge bases per chatbot — the bot searches across all active ones.

### Creating a Knowledge Base

1. Go to **Knowledge** in the sidebar
2. Click **+ New Knowledge Base**
3. Give it a name (e.g., "Course Information", "FAQ", "Policies")
4. The KB is created and activated

### Adding Content — Three Methods

#### Method A: Q&A Pairs (Direct Training) — Recommended

Q&A pairs are the most reliable method. Each pair is:
- Stored with a vector embedding for semantic search
- Matched against user questions by meaning, not just keywords
- Returned as context to the LLM when relevant

To add a Q&A pair:
1. Open the knowledge base
2. Click **+ Add Q&A**
3. Fill in:
   - **Question** — The primary question (e.g., "How much does the AI Engineer course cost?")
   - **Answer** — The full answer
   - **Category** — Optional grouping (e.g., "Pricing", "Enrollment")
   - **Sub-category** — Optional sub-grouping
   - **Relevant Questions** — Alternative phrasings, separated by `/`
   - **Linkable Suggestion** — Optional HTML appended to the answer (e.g., a link to the enrollment page)

#### Method B: Bulk Upload Excel/CSV

See the [next section](#6-upload-training-data-excelcsv) for full details.

#### Method C: Document Upload

Upload PDF, DOCX, TXT, or CSV files:
1. Click **Upload Document**
2. Select your file
3. The system extracts text, splits it into chunks, and embeds each chunk
4. The document is immediately searchable

#### Method D: Manual Text Document

1. Click **Add Manual Document**
2. Enter a title and paste the content
3. The document is chunked and embedded automatically

### After Adding New Q&A Pairs

New Q&A pairs are embedded immediately when added via the admin UI. If you notice new pairs are not showing up in chat results, click **Sync Embeddings** on the knowledge base — this re-embeds any pairs that may have missed their embedding step.

### Reordering Q&A Pairs

Drag and drop Q&A pairs to reorder them. The sort order affects display in the admin UI (not search ranking — ranking is always by semantic similarity score).

---

## 6. Upload Training Data (Excel/CSV)

This is the fastest way to bulk-load Q&A content from spreadsheets.

### File Format

Create an Excel (`.xlsx` / `.xls`) or CSV file with these columns:

| Column Name | Required | Description |
|---|---|---|
| `question` | ✅ Yes | Primary question (also accepts: `q`, `title`) |
| `answer` | ✅ Yes | Full answer text (also accepts: `long answer`, `response`, `description`) |
| `category` | No | Category label (also accepts: `type`, `topic`) |
| `sub-category` | No | Sub-category (also accepts: `subcategory`, `tags`) |
| `relevant questions` | No | Slash-separated alternate phrasings |
| `linkable suggestion` | No | HTML string appended to answer (e.g., a CTA button) |

Column names are case-insensitive and flexible — the system matches common variations automatically.

### Example Spreadsheet

| question | answer | category | relevant questions |
|---|---|---|---|
| How much does the AI Engineer course cost? | The Professional AI Engineer course costs 10,000 BDT for the full program. | Pricing | What is the course fee / How much to enroll / Course price |
| How long is the AI Engineer course? | The course runs for 12 intensive sessions over 3 months. | Duration | Course length / Program duration |
| How do I enroll? | Visit ictbangladesh.com.bd and click Enroll Now, or contact us at support@ictbangladesh.com.bd | Enrollment | Sign up / Registration / How to join |

### Uploading

**Via Admin Dashboard:**
1. Go to **Knowledge** → select a knowledge base
2. Click **📤 Upload Training Data**
3. Select your Excel or CSV file
4. Optionally check **Clear existing Q&A pairs** to replace all existing pairs
5. Click Upload

**Via API:**
```bash
curl -X POST \
  "https://your-server.com/api/v1/organizations/{org_id}/knowledge-bases/{kb_id}/training-data/upload" \
  -H "Authorization: Bearer <token>" \
  -F "file=@training_data.xlsx" \
  -F "clear_existing=false"
```

**Response:**
```json
{
  "inserted": 47,
  "skipped": 2,
  "errors": [],
  "total_rows": 49
}
```

### After Upload

Each uploaded row is automatically embedded using the configured embedding model. The pairs are immediately searchable by the chatbot. No manual sync step needed for bulk uploads — embeddings are created during the upload process.

---

## 7. Embed the Chat Widget

### Method A: Script Tag (Easiest — any website)

Add this single line before `</body>` on any webpage:

```html
<script
  src="https://your-server.com/chatbot-widget.js"
  data-org-id="YOUR_ORG_ID"
  data-chatbot-id="YOUR_CHATBOT_ID"
  data-api-url="https://your-server.com/api/v1"
></script>
```

The widget automatically uses the persona, theme, and greeting configured in your Settings.

Widget configuration attributes (all optional — override Settings defaults):

| Attribute | Description |
|---|---|
| `data-org-id` | Your organization UUID (required) |
| `data-chatbot-id` | Your chatbot UUID (required) |
| `data-api-url` | API base URL (defaults to same origin) |
| `data-theme` | Override primary color (hex, e.g., `#3B82F6`) |
| `data-title` | Override chat header title |
| `data-position` | `bottom-right` (default) or `bottom-left` |

### Method B: Direct HTML Integration

The default chat interface is served at `https://your-server.com/` and can be used as a standalone page or embedded in an iframe.

### Method C: React Component (Custom Integration)

For React applications that need tighter integration:

```jsx
import { useState, useEffect, useRef } from 'react';

const API_URL = 'https://your-server.com/api/v1';
const ORG_ID = 'your-org-uuid';
const CHATBOT_ID = 'your-chatbot-uuid';

function ChatWidget() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState(null);

  // Create session on mount
  useEffect(() => {
    fetch(`${API_URL}/chat/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        org_id: ORG_ID,
        chatbot_id: CHATBOT_ID,
        end_user_identifier: 'user_' + Date.now(),
        channel: 'web_widget',
      }),
    })
      .then(r => r.json())
      .then(data => setSessionId(data.id));
  }, []);

  async function sendMessage() {
    if (!input.trim() || !sessionId) return;
    const text = input.trim();
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setInput('');

    const res = await fetch(`${API_URL}/chat/sessions/${sessionId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: text }),
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let botText = '';
    setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      for (const line of decoder.decode(value).split('\n')) {
        if (line.startsWith('data: ')) {
          try {
            const evt = JSON.parse(line.slice(6));
            if (evt.type === 'token' && evt.content) {
              botText += evt.content;
              setMessages(prev => {
                const updated = [...prev];
                updated[updated.length - 1] = { role: 'assistant', content: botText };
                return updated;
              });
            }
          } catch {}
        }
      }
    }
  }

  return (
    <div style={{ maxWidth: 600, margin: '0 auto', padding: 16 }}>
      <div style={{ height: 400, overflowY: 'auto', border: '1px solid #ccc', padding: 8 }}>
        {messages.map((m, i) => (
          <div key={i} style={{ textAlign: m.role === 'user' ? 'right' : 'left', margin: '8px 0' }}>
            <span style={{ background: m.role === 'user' ? '#3B82F6' : '#f3f4f6', color: m.role === 'user' ? '#fff' : '#000', padding: '6px 12px', borderRadius: 8, display: 'inline-block' }}>
              {m.content}
            </span>
          </div>
        ))}
      </div>
      <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && sendMessage()}
          style={{ flex: 1, padding: '8px 12px', border: '1px solid #ccc', borderRadius: 6 }}
          placeholder="Type a message..."
        />
        <button onClick={sendMessage} style={{ padding: '8px 16px', background: '#3B82F6', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}>
          Send
        </button>
      </div>
    </div>
  );
}
```

### SSE Event Reference

Messages are streamed as Server-Sent Events:

```
data: {"type": "token", "content": "Hello"}
data: {"type": "token", "content": " there!"}
data: {"type": "done", "confidence": 0.87, "eil_score": 0.92, "suggestions": ["What courses are available?"], "fallback_contacts": []}
```

| Event type | Fields | Description |
|---|---|---|
| `token` | `content` | Streaming text chunk |
| `done` | `confidence`, `eil_score`, `suggestions`, `fallback_contacts` | Stream complete + metadata |

Use `suggestions` to show clickable follow-up question chips to the user.

---

## 8. Language Support

The bot automatically detects the language of each user message and responds in the same language. No configuration is needed for this to work.

**How it works:**
1. Each user message is analyzed for language (using `langdetect`)
2. If non-English is detected, an absolute language instruction is injected: *"You MUST respond ENTIRELY in Bengali"* (or detected language)
3. The language setting persists for the conversation session
4. If the user switches back to English mid-conversation, the bot also switches back

**Supported languages:** Any language supported by `langdetect` (80+ languages). The LLM (llama3.2) handles Bengali, Arabic, Hindi, Spanish, French, and other major languages well.

**Default language:** Set in Settings → Persona & Chat → Default Language. Used when language detection is inconclusive.

**Tip:** Include Bengali (বাংলা) Q&A pairs in your knowledge base for best Bengali-language results. The RAG search is language-agnostic (embedding-based) so it matches meaning regardless of script.

---

## 9. Monitor Conversations

Go to **Conversations** in the sidebar to see all chat sessions.

### Conversation List

- Sortable by date, status
- Filter by: All / Active / Escalated
- Search by user identifier or message content

### Conversation View

Click any conversation to see the full message thread:
- User messages (right-aligned, blue)
- Bot messages (left-aligned, gray) with markdown rendered
- Escalation status if applicable
- Confidence scores per response (available in the metadata)

### Analytics

Go to **Analytics** for aggregated data:
- Total conversations (daily/weekly/monthly)
- Message volume
- RAG hit rate (% of questions answered from knowledge base vs. general LLM knowledge)
- Language distribution
- Top question categories

---

## 10. Human Escalation

When a user asks to speak with a human, or when the bot cannot confidently answer, the conversation is flagged for escalation.

### User triggers escalation by saying:
- "Talk to a human"
- "Connect me to an agent"
- "I want to speak to someone"

### Admin handles escalation:
1. Go to **Conversations** → filter by **Escalated**
2. Click the escalated conversation
3. Read the full context
4. Type a reply in the agent input box and click Send
5. The user sees the reply in their chat widget

### Email notification
If SMTP is configured in `.env`, the admin receives an email when a new escalation is created.

### Resolving escalations
Click **Resolve** to mark the conversation as handled and return it to normal status.

---

## 11. Token Usage & Billing

Tokens are usage credits deducted for each AI operation (embedding, chat, document ingestion).

### View your balance

Go to **Settings** → **Billing** tab, or check the token balance shown on the Overview page.

### When tokens run out

The chatbot will stop responding to users until tokens are topped up. Contact your Super Admin to add credits.

### Token costs (approximate)

| Operation | Token cost |
|---|---|
| Chat message (with RAG) | ~500–2,000 per response |
| Document embedding (per chunk) | ~50–200 |
| Q&A pair embedding | ~50 |
| Training data upload (per row) | ~50 |

Actual cost depends on response length and document complexity.

---

## 12. Super Admin — Managing Tenants

The **Super Admin** panel is only visible to users with the super_admin role.

### Tenant List

Shows all organizations with:
- Name, status (active/suspended), plan
- Token balance
- Member count
- Created date

### Per-tenant actions

| Action | Description |
|---|---|
| ⚙ Settings | Open tenant details panel (token balance, org info) |
| 🔋 Tokens | Open token top-up modal |
| Suspend | Immediately blocks all chat for this tenant |
| Activate | Re-enables a suspended tenant |
| Delete | Permanently removes the organization and all data |

### Token Top-Up

1. Click **🔋 Tokens** on any organization row
2. Use the preset buttons: **+100K**, **+500K**, **+1M**
3. Or enter a custom amount
4. Click **Top Up** — the balance is updated instantly

### Creating a New Tenant

1. Go to Super Admin → click **+ New Organization**
2. Fill in:
   - Organization name
   - Admin email (the owner's login email)
   - Plan / subscription tier
3. The organization is created and the admin user receives login credentials

### Accessing Tenant Settings

1. Click **⚙ Settings** on any organization row
2. The tenant settings panel opens showing:
   - Org ID and slug
   - Current token balance
   - Subscription details
   - Quick actions: top-up, suspend/activate

---

## Quick Reference: Training Data Template

Download or copy this template for your Excel upload:

| question | answer | category | sub-category | relevant questions | linkable suggestion |
|---|---|---|---|---|---|
| What is [your product]? | [Full description] | General | | [alt question 1] / [alt question 2] | |
| How much does it cost? | [Pricing details] | Pricing | | Cost / Price / Fee | |
| How do I sign up? | [Enrollment steps] | Enrollment | | Register / Join / Enroll | `<a href="https://yoursite.com/enroll">Enroll Now →</a>` |

**Tips for better RAG results:**
- Write questions exactly as users would ask them (conversational style)
- Include common misspellings and alternate phrasings in **Relevant Questions**
- Keep answers concise (2–5 sentences) — long answers reduce search precision
- Use consistent category names to make filtering easier in the admin UI
- Add a **Linkable Suggestion** for actions (enrollment, contact, booking) to create clickable CTAs in the chat
