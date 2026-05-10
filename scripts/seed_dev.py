"""
Dev Seed Script — Business AI Assistant Platform
=================================================
Verifies test accounts exist and prints a credential/URL reference table.
Configure the accounts below to match your local development database.

Usage:
    python scripts/seed_dev.py

What it does:
  1. Checks if the local server is reachable
  2. Prints a formatted reference table of configured accounts and URLs
  3. Lists setup steps for first-time developers
"""

import asyncio
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Test accounts — configure for your local environment ─────────────────────
#
# Update these with the accounts you created during setup.
# NEVER commit real credentials — this file is for local dev reference only.
#
TEST_ACCOUNTS = [
    # (email,                  password,      role)
    ("superadmin@example.com", "ChangeMe!1",  "super_admin"),
    ("admin@yourorg.com",      "ChangeMe!2",  "org_admin"),
    ("demo@example.com",       "ChangeMe!3",  "org_admin"),
]

BASE_URL = os.getenv("BASE_URL", "http://localhost:9000")


async def main():
    print()
    print("=" * 65)
    print("  BUSINESS AI ASSISTANT PLATFORM — Dev Reference")
    print("=" * 65)
    print()

    print("  CONFIGURED TEST ACCOUNTS")
    print("  " + "─" * 60)
    for email, pw, role in TEST_ACCOUNTS:
        print(f"  [{role}]  {email}  /  {pw}")
    print()

    print("  URLs")
    print("  " + "─" * 60)
    print(f"  Chat Widget   : {BASE_URL}/")
    print(f"  Admin Panel   : {BASE_URL}/admin")
    print(f"  API Docs      : {BASE_URL}/docs")
    print(f"  Health Check  : {BASE_URL}/health")
    print()

    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as c:
            r = await c.get(f"{BASE_URL}/health")
            status = "ONLINE" if r.status_code == 200 else f"HTTP {r.status_code}"
    except Exception:
        status = "OFFLINE"

    print(f"  Server status : {status}")
    print()
    print("  FIRST-TIME SETUP")
    print("  " + "─" * 60)
    print("  1. cp .env.example .env   (fill in DATABASE_URL, OLLAMA_BASE_URL)")
    print("  2. psql -d ai_chatbot_db -f migrations/001_initial.sql")
    print("  3. uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload")
    print("  4. POST /api/v1/auth/register  (create super admin)")
    print("  5. Open /admin and create your first org + chatbot")
    print()
    print("  Update TEST_ACCOUNTS above with your local credentials.")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
