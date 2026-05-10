"""
Integration test suite — Business AI Assistant Platform
=======================================================
Run: python scripts/run_tests.py

Tests every major area:
  Auth, Orgs, Chatbots, Knowledge Base, RAG Search,
  AI Providers, Conversations, Analytics, Bulk Upload, Live Chat

Configuration (environment variables or defaults):
  BASE_URL          http://localhost:9000/api/v1
  TEST_SA_EMAIL     superadmin@example.com
  TEST_SA_PASSWORD  ChangeMe!1
  TEST_ORG_EMAIL    admin@yourorg.com
  TEST_ORG_PASSWORD ChangeMe!2
  TEST_ORG_ID       (UUID of your test organization — from DB or admin panel)
  TEST_CB_ID        (UUID of your test chatbot)
  TEST_KB_ID        (UUID of your test knowledge base)

How to get IDs:
  1. Start the server and open /admin
  2. Create an org, chatbot, and knowledge base
  3. Copy the UUIDs from the URL or from GET /api/v1/organizations
  4. Export them as environment variables, or edit the defaults below
"""

import asyncio
import io
import os
import sys
import httpx

BASE = os.getenv("BASE_URL", "http://localhost:9000/api/v1")

# ── Credentials — set via environment variables ───────────────────────────────
SA_EMAIL    = os.getenv("TEST_SA_EMAIL",     "superadmin@example.com")
SA_PASS     = os.getenv("TEST_SA_PASSWORD",  "ChangeMe!1")
ORG_EMAIL   = os.getenv("TEST_ORG_EMAIL",    "admin@yourorg.com")
ORG_PASS    = os.getenv("TEST_ORG_PASSWORD", "ChangeMe!2")

# ── Resource IDs — set via environment variables ──────────────────────────────
ORG = os.getenv("TEST_ORG_ID", "")   # UUID of your test organization
CB  = os.getenv("TEST_CB_ID",  "")   # UUID of your test chatbot
KB  = os.getenv("TEST_KB_ID",  "")   # UUID of your test knowledge base

PASS = 0
FAIL = 0


def H(token):
    return {"Authorization": f"Bearer {token}"}


def section(title):
    print(f"\n-- {title} {'-' * (55 - len(title))}")


async def chk(c, label, method, url, expect_key=None, **kw):
    global PASS, FAIL
    try:
        r = await getattr(c, method)(url, **kw)
        if 200 <= r.status_code < 300:
            if expect_key:
                body = r.json()
                found = (
                    (isinstance(body, list) and len(body) > 0 and expect_key in str(body[0]))
                    or (isinstance(body, dict) and expect_key in str(body))
                )
                if found:
                    print(f"  PASS [{r.status_code}] {label}")
                    PASS += 1
                else:
                    print(f"  FAIL [{r.status_code}] {label} -- key '{expect_key}' not in response")
                    FAIL += 1
            else:
                print(f"  PASS [{r.status_code}] {label}")
                PASS += 1
        else:
            print(f"  FAIL [{r.status_code}] {label}")
            FAIL += 1
    except Exception as e:
        print(f"  FAIL [ERR] {label} -- {e}")
        FAIL += 1


async def chat_ask(c, session_id, question, expect_fragment):
    global PASS, FAIL
    full = ""
    try:
        async with c.stream(
            "POST",
            f"{BASE}/chat/stream?chatbot_id={CB}&session_id={session_id}",
            json={"content": question, "type": "text"},
            timeout=60,
        ) as r:
            async for line in r.aiter_lines():
                if line.startswith("data: "):
                    try:
                        import json as _json
                        d = _json.loads(line[6:])
                        if d.get("type") == "token":
                            full += d.get("content", "")
                    except Exception:
                        pass
        if expect_fragment.lower() in full.lower():
            print(f"  PASS [chat] Q: {question[:60]}")
            print(f"              A: {full[:115]}")
            PASS += 1
        else:
            print(f"  FAIL [chat] Q: {question[:60]}")
            print(f"              Expected '{expect_fragment}' -- got: {full[:80]}")
            FAIL += 1
    except Exception as e:
        print(f"  FAIL [chat] {question[:60]} -- {e}")
        FAIL += 1


async def main():
    global PASS, FAIL

    if not ORG or not CB or not KB:
        print("ERROR: Set TEST_ORG_ID, TEST_CB_ID, TEST_KB_ID environment variables.")
        print("       See the script header for instructions.")
        sys.exit(1)

    async with httpx.AsyncClient(timeout=40) as c:

        # ── 1. Auth ────────────────────────────────────────────────────────────
        section("1. AUTHENTICATION")
        r = await c.post(f"{BASE}/auth/login", json={"email": SA_EMAIL, "password": SA_PASS})
        if r.status_code != 200:
            print(f"  FAIL [auth] Super admin login failed ({r.status_code}). Check TEST_SA_EMAIL/TEST_SA_PASSWORD.")
            sys.exit(1)
        SA_TOKEN = r.json()["tokens"]["access_token"]
        print(f"  PASS [200] Login super_admin  {SA_EMAIL}")
        PASS += 1

        r = await c.post(f"{BASE}/auth/login", json={"email": ORG_EMAIL, "password": ORG_PASS})
        if r.status_code != 200:
            print(f"  FAIL [auth] Org admin login failed ({r.status_code}). Check TEST_ORG_EMAIL/TEST_ORG_PASSWORD.")
            sys.exit(1)
        ICT_TOKEN = r.json()["tokens"]["access_token"]
        print(f"  PASS [200] Login org admin    {ORG_EMAIL}")
        PASS += 1

        await chk(c, "GET /auth/me  (org admin)",   "get", f"{BASE}/auth/me", headers=H(ICT_TOKEN))
        await chk(c, "GET /auth/me  (super_admin)", "get", f"{BASE}/auth/me", headers=H(SA_TOKEN))

        # ── 2. Organizations ───────────────────────────────────────────────────
        section("2. ORGANIZATIONS")
        await chk(c, "List orgs (super_admin)", "get", f"{BASE}/organizations",                      headers=H(SA_TOKEN))
        await chk(c, "Get test org",            "get", f"{BASE}/organizations/{ORG}",                headers=H(ICT_TOKEN))
        await chk(c, "List members",            "get", f"{BASE}/organizations/{ORG}/members",        headers=H(ICT_TOKEN))
        await chk(c, "Token balance",           "get", f"{BASE}/organizations/{ORG}/tokens/balance", headers=H(ICT_TOKEN))
        await chk(c, "Subscription (active)",   "get", f"{BASE}/organizations/{ORG}/subscription",   headers=H(ICT_TOKEN))

        # ── 3. Chatbots ────────────────────────────────────────────────────────
        section("3. CHATBOTS")
        await chk(c, "List chatbots",      "get", f"{BASE}/organizations/{ORG}/chatbots",                    headers=H(ICT_TOKEN))
        await chk(c, "Get chatbot",        "get", f"{BASE}/organizations/{ORG}/chatbots/{CB}",               headers=H(ICT_TOKEN))
        await chk(c, "Get persona",        "get", f"{BASE}/organizations/{ORG}/chatbots/{CB}/persona",       headers=H(ICT_TOKEN))
        await chk(c, "List prompts",       "get", f"{BASE}/organizations/{ORG}/chatbots/{CB}/prompts",       headers=H(ICT_TOKEN))
        await chk(c, "List guardrails",    "get", f"{BASE}/organizations/{ORG}/chatbots/{CB}/guardrails",    headers=H(ICT_TOKEN))
        await chk(c, "List deployments",   "get", f"{BASE}/organizations/{ORG}/chatbots/{CB}/deployments",   headers=H(ICT_TOKEN))
        await chk(c, "List model-configs", "get", f"{BASE}/organizations/{ORG}/chatbots/{CB}/model-configs", headers=H(ICT_TOKEN))
        await chk(c, "List end-users",     "get", f"{BASE}/organizations/{ORG}/chatbots/{CB}/end-users",     headers=H(ICT_TOKEN))

        # ── 4. Knowledge Base ──────────────────────────────────────────────────
        section("4. KNOWLEDGE BASE")
        await chk(c, "List KBs (chatbot)",  "get", f"{BASE}/organizations/{ORG}/chatbots/{CB}/knowledge-bases",          headers=H(ICT_TOKEN))
        await chk(c, "Get KB",              "get", f"{BASE}/organizations/{ORG}/knowledge-bases/{KB}",                   headers=H(ICT_TOKEN))
        await chk(c, "List Q&A (limit 10)", "get", f"{BASE}/organizations/{ORG}/knowledge-bases/{KB}/qa-pairs?limit=10", headers=H(ICT_TOKEN))
        await chk(c, "List documents",      "get", f"{BASE}/organizations/{ORG}/knowledge-bases/{KB}/documents",         headers=H(ICT_TOKEN))
        await chk(c, "List sources",        "get", f"{BASE}/organizations/{ORG}/knowledge-bases/{KB}/sources",           headers=H(ICT_TOKEN))

        r = await c.post(f"{BASE}/organizations/{ORG}/knowledge-bases/{KB}/search",
                         headers=H(ICT_TOKEN),
                         json={"query": "test query", "top_k": 5, "threshold": 0.3})
        if r.status_code == 200:
            results = r.json()
            score = results[0]['score'] if results else 0
            print(f"  PASS [200] RAG search  (results={len(results)}, top_score={score:.4f})")
            PASS += 1
        else:
            print(f"  FAIL [{r.status_code}] RAG search"); FAIL += 1

        # ── 5. Bulk Upload ─────────────────────────────────────────────────────
        section("5. BULK UPLOAD")
        csv_bytes = b"question,answer,category\nIntegration test Q?,Integration test answer.,Testing\n"
        r = await c.post(
            f"{BASE}/organizations/{ORG}/knowledge-bases/{KB}/training-data/upload",
            headers=H(ICT_TOKEN),
            files={"file": ("integration.csv", io.BytesIO(csv_bytes), "text/csv")},
            data={"clear_existing": "false"},
        )
        if r.status_code == 200 and r.json().get("inserted", 0) >= 1:
            d = r.json()
            print(f"  PASS [200] Bulk upload CSV  (inserted={d['inserted']}, embedded={d.get('embedded','-')}, skipped={d['skipped']})")
            PASS += 1
        else:
            print(f"  FAIL [{r.status_code}] Bulk upload -- {r.text[:100]}"); FAIL += 1

        # ── 6. AI Providers ────────────────────────────────────────────────────
        section("6. AI PROVIDERS")
        await chk(c, "List AI providers", "get", f"{BASE}/organizations/{ORG}/ai-providers", headers=H(ICT_TOKEN))

        # ── 7. Conversations & Escalations ─────────────────────────────────────
        section("7. CONVERSATIONS & ESCALATIONS")
        await chk(c, "List conversations", "get", f"{BASE}/organizations/{ORG}/conversations?limit=5", headers=H(ICT_TOKEN))
        await chk(c, "List escalations",   "get", f"{BASE}/organizations/{ORG}/escalations",           headers=H(ICT_TOKEN))

        # ── 8. Analytics ───────────────────────────────────────────────────────
        section("8. ANALYTICS")
        await chk(c, "Dashboard stats", "get", f"{BASE}/organizations/{ORG}/analytics/dashboard",          headers=H(ICT_TOKEN))
        await chk(c, "Audit logs",      "get", f"{BASE}/organizations/{ORG}/analytics/audit-logs?limit=5", headers=H(ICT_TOKEN))

        # ── 9. Chat Widget (public) ────────────────────────────────────────────
        section("9. CHAT WIDGET (public, no auth)")
        import time
        SID = f"integration_{int(time.time())}"
        r = await c.post(f"{BASE}/chat/session",
                         json={"chatbot_id": CB, "session_id": SID,
                               "end_user_identifier": "test_user_001", "channel": "web_widget"})
        if 200 <= r.status_code < 300:
            print(f"  PASS [{r.status_code}] Create chat session  (id={SID})")
            PASS += 1
        else:
            print(f"  FAIL [{r.status_code}] Create chat session"); FAIL += 1

        await chk(c, "Get chat history", "get", f"{BASE}/chat/history?chatbot_id={CB}&session_id={SID}")

        # ── 10. Live Chat — RAG Answers ────────────────────────────────────────
        # Customize these questions to match your knowledge base content
        section("10. LIVE CHAT -- RAG ANSWERS")
        test_questions = [
            ("What services do you offer?",     "service"),
            ("How do I get started?",           "start"),
            ("What is your pricing?",           "price"),
        ]
        for question, fragment in test_questions:
            await chat_ask(c, SID, question, fragment)

    # ── Summary ────────────────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print(f"  TOTAL:  {PASS} passed    {FAIL} failed")
    if FAIL == 0:
        print("  STATUS: ALL TESTS PASSED")
    else:
        print(f"  STATUS: {FAIL} FAILURE(S) -- see above")
    print("=" * 60)
    return FAIL


if __name__ == "__main__":
    fail_count = asyncio.run(main())
    sys.exit(fail_count)
