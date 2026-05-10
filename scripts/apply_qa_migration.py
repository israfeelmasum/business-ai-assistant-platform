"""Apply knowledge_qa_pairs migration."""
import asyncio, asyncpg, urllib.parse, sys

async def go():
    sys.stdout.write("Connecting...\n"); sys.stdout.flush()
    p = urllib.parse.urlparse('postgresql://postgres:Lw0DhdD%7BNsD%254%23PG@65.118.64.4:5432/ai_chatbot_db')
    c = await asyncpg.connect(
        host=p.hostname, port=p.port,
        database=p.path.lstrip('/'),
        user=p.username,
        password=urllib.parse.unquote(p.password),
        timeout=10
    )
    sys.stdout.write("Connected\n"); sys.stdout.flush()
    await c.execute('ALTER TABLE knowledge_qa_pairs ADD COLUMN IF NOT EXISTS category VARCHAR(100)')
    sys.stdout.write("category: OK\n"); sys.stdout.flush()
    await c.execute('ALTER TABLE knowledge_qa_pairs ADD COLUMN IF NOT EXISTS sort_order INTEGER DEFAULT 0')
    sys.stdout.write("sort_order: OK\n"); sys.stdout.flush()
    rows = await c.fetch("SELECT column_name FROM information_schema.columns WHERE table_name='knowledge_qa_pairs' ORDER BY column_name")
    cols = [r['column_name'] for r in rows]
    sys.stdout.write(f"Columns: {cols}\n"); sys.stdout.flush()
    await c.close()
    sys.stdout.write("Done\n"); sys.stdout.flush()

asyncio.run(go())
