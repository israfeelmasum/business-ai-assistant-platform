"""
Platform migration script — run once to apply schema changes.
Adds: analytics_reports table, chatbot_themes new columns,
      knowledge_qa_pairs new columns.
"""
import asyncio
import urllib.parse
import asyncpg

DATABASE_URL = "postgresql+asyncpg://postgres:Lw0DhdD%7BNsD%254%23PG@65.118.64.4:5432/ai_chatbot_db"


def parse_db_url(url: str):
    raw = url.replace("postgresql+asyncpg://", "postgresql://")
    p = urllib.parse.urlparse(raw)
    return dict(
        host=p.hostname,
        port=p.port,
        database=p.path.lstrip("/"),
        user=p.username,
        password=urllib.parse.unquote(p.password),
    )


async def run():
    params = parse_db_url(DATABASE_URL)
    print(f"Connecting to {params['user']}@{params['host']}:{params['port']}/{params['database']}")
    conn = await asyncpg.connect(**params)

    # ── analytics_reports ─────────────────────────────────────────────────────
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS analytics_reports (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            org_id              UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            chatbot_id          UUID REFERENCES chatbots(id) ON DELETE SET NULL,
            period_type         VARCHAR(20) NOT NULL,
            period_label        VARCHAR(20) NOT NULL,
            period_start        DATE NOT NULL,
            period_end          DATE NOT NULL,
            total_conversations INTEGER DEFAULT 0,
            total_messages      INTEGER DEFAULT 0,
            escalation_count    INTEGER DEFAULT 0,
            escalation_rate     DOUBLE PRECISION DEFAULT 0.0,
            avg_confidence      DOUBLE PRECISION DEFAULT 0.0,
            unique_users        INTEGER DEFAULT 0,
            top_questions       JSONB DEFAULT '[]'::jsonb,
            staff_stats         JSONB DEFAULT '[]'::jsonb,
            ai_summary          TEXT,
            generated_at        TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    print("analytics_reports table: OK")

    await conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_analytics_reports_org ON analytics_reports(org_id)"
    )
    await conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_analytics_reports_bot ON analytics_reports(chatbot_id)"
    )
    print("analytics_reports indexes: OK")

    # ── chatbot_themes new columns ─────────────────────────────────────────────
    theme_cols = [
        ("logo_url",          "TEXT"),
        ("welcome_message",   "TEXT"),
        ("fallback_whatsapp", "VARCHAR(30)"),
        ("fallback_email",    "VARCHAR(255)"),
        ("fallback_phone",    "VARCHAR(30)"),
        ("fallback_message",  "TEXT"),
    ]
    for col, defn in theme_cols:
        try:
            await conn.execute(
                f"ALTER TABLE chatbot_themes ADD COLUMN IF NOT EXISTS {col} {defn}"
            )
            print(f"chatbot_themes.{col}: OK")
        except Exception as exc:
            print(f"chatbot_themes.{col}: {exc}")

    # ── knowledge_qa_pairs new columns ────────────────────────────────────────
    qa_cols = [
        ("category",   "VARCHAR(100)"),
        ("sort_order", "INTEGER NOT NULL DEFAULT 0"),
    ]
    for col, defn in qa_cols:
        try:
            await conn.execute(
                f"ALTER TABLE knowledge_qa_pairs ADD COLUMN IF NOT EXISTS {col} {defn}"
            )
            print(f"knowledge_qa_pairs.{col}: OK")
        except Exception as exc:
            print(f"knowledge_qa_pairs.{col}: {exc}")

    await conn.close()
    print("\nAll migrations applied successfully.")


if __name__ == "__main__":
    asyncio.run(run())
