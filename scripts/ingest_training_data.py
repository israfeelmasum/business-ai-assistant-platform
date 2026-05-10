"""
Training data ingestion script.
Reads Q&A pairs from an Excel/CSV file and inserts them into a knowledge base
with embeddings generated via the configured Ollama server.

Usage:
    python scripts/ingest_training_data.py \
        --file "C:/path/to/data.xlsx" \
        --kb-id f5753f29-300d-4410-b865-e2b670d6bf01 \
        --org-id 25d58968-0fae-48b6-9898-748534ce86c2 \
        [--clear] [--batch-size 20]

Column mapping (auto-detected, case-insensitive):
    question   : question / primary question / q / title
    answer     : answer / long answer / a / response / description
    category   : category / type / topic
    tags       : tags / sub-category / sub category / subcategory
    suggestion : linkable suggestion / suggestion / link suggestion
"""

import argparse
import asyncio
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import asyncpg
import httpx
import numpy as np
import pandas as pd
from pgvector.asyncpg import register_vector

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────────
DB_HOST     = "65.118.64.4"
DB_PORT     = 5432
DB_NAME     = "ai_chatbot_db"
DB_USER     = "postgres"
DB_PASS     = "Lw0DhdD{NsD%4#PG"

OLLAMA_URL  = "https://ollama.us.ai.apibox.link"
EMBED_MODEL = "nomic-embed-text"

# Column name aliases (lowercase → canonical field)
COL_ALIASES = {
    "question"           : "question",
    "primary question"   : "question",
    "q"                  : "question",
    "title"              : "question",

    "answer"             : "answer",
    "long answer"        : "answer",
    "a"                  : "answer",
    "response"           : "answer",
    "description"        : "answer",

    "short answer"       : "short_answer",   # kept separate — appended when no long answer

    "category"           : "category",
    "type"               : "category",
    "topic"              : "category",

    "sub-category"       : "sub_category",
    "sub category"       : "sub_category",
    "subcategory"        : "sub_category",
    "tags"               : "tags",

    "relevant questions" : "relevant_questions",
    "related questions"  : "relevant_questions",

    "linkable suggestion": "suggestion",
    "suggestion"         : "suggestion",
    "link suggestion"    : "suggestion",
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def detect_columns(df: pd.DataFrame) -> dict:
    """Map DataFrame columns → canonical field names."""
    mapping = {}
    for col in df.columns:
        canonical = COL_ALIASES.get(col.strip().lower())
        if canonical:
            mapping[canonical] = col
    return mapping


def build_rows(df: pd.DataFrame, mapping: dict) -> list[dict]:
    """Convert DataFrame rows to ingestion dicts."""
    rows = []
    for _, row in df.iterrows():
        def get(field, default=""):
            col = mapping.get(field)
            if col and pd.notna(row.get(col, None)):
                return str(row[col]).strip()
            return default

        question = get("question")
        if not question:
            continue  # skip rows with no question

        # Prefer long answer; fall back to short answer
        answer = get("answer") or get("short_answer")
        if not answer:
            continue

        # Append suggestion to answer
        suggestion = get("suggestion")
        if suggestion:
            answer = f"{answer}\n\n{suggestion}"

        # Category = "Category / Sub-Category" or just category
        cat_parts = [p for p in [get("category"), get("sub_category")] if p]
        category = " / ".join(cat_parts) if cat_parts else None

        # Tags from sub_category + relevant questions
        tags = []
        sub_cat = get("sub_category")
        if sub_cat:
            tags.append(sub_cat)
        cat = get("category")
        if cat and cat not in tags:
            tags.append(cat)
        rel_qs = get("relevant_questions")
        if rel_qs:
            for q in rel_qs.replace(" / ", "/").split("/"):
                q = q.strip()
                if q and len(q) < 100:  # exclude very long strings
                    tags.append(q)

        rows.append({
            "question": question,
            "answer": answer,
            "category": category,
            "tags": tags,
        })
    return rows


async def get_embedding(client: httpx.AsyncClient, text: str) -> Optional[list[float]]:
    """Call Ollama embeddings endpoint."""
    try:
        resp = await client.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["embedding"]
    except Exception as e:
        log.warning(f"Embedding failed: {e}")
        return None


async def generate_embeddings(rows: list[dict], batch_size: int = 10) -> list[dict]:
    """Generate embeddings for all rows, in batches."""
    log.info(f"Generating embeddings for {len(rows)} rows (batch={batch_size})...")
    async with httpx.AsyncClient() as client:
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            tasks = [get_embedding(client, r["question"]) for r in batch]
            embeddings = await asyncio.gather(*tasks)
            for row, emb in zip(batch, embeddings):
                row["embedding"] = emb
            done = min(i + batch_size, len(rows))
            log.info(f"  {done}/{len(rows)} embeddings done")
    return rows


async def ingest(
    file_path: str,
    kb_id: str,
    org_id: str,
    clear: bool = False,
    batch_size: int = 20,
) -> None:
    # ── Load file ─────────────────────────────────────────────────────────
    path = Path(file_path)
    if path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(file_path)
    elif path.suffix.lower() == ".csv":
        df = pd.read_csv(file_path)
    else:
        sys.exit(f"Unsupported file type: {path.suffix}")

    log.info(f"Loaded {len(df)} rows from {path.name}")
    log.info(f"Columns: {list(df.columns)}")

    mapping = detect_columns(df)
    log.info(f"Column mapping: {mapping}")

    if "question" not in mapping or ("answer" not in mapping and "short_answer" not in mapping):
        sys.exit("Could not find required columns (question + answer) in file.")

    rows = build_rows(df, mapping)
    log.info(f"Valid rows after filtering: {len(rows)}")

    # ── Generate embeddings ───────────────────────────────────────────────
    rows = await generate_embeddings(rows, batch_size=batch_size)

    # ── Connect to DB ─────────────────────────────────────────────────────
    conn = await asyncpg.connect(
        host=DB_HOST, port=DB_PORT, database=DB_NAME,
        user=DB_USER, password=DB_PASS,
    )
    await register_vector(conn)

    try:
        async with conn.transaction():
            if clear:
                await conn.execute(
                    "DELETE FROM knowledge_qa_pairs WHERE knowledge_base_id = $1",
                    uuid.UUID(kb_id),
                )
                log.info(f"Cleared existing rows from KB")

            # Get current max sort_order
            max_order = await conn.fetchval(
                "SELECT COALESCE(MAX(sort_order), -1) FROM knowledge_qa_pairs WHERE knowledge_base_id = $1",
                uuid.UUID(kb_id),
            )

            inserted = 0
            now = datetime.now(timezone.utc)

            for idx, row in enumerate(rows):
                emb = row.get("embedding")
                emb_np = np.array(emb, dtype=np.float32) if emb else None

                await conn.execute(
                    """
                    INSERT INTO knowledge_qa_pairs
                        (id, knowledge_base_id, org_id, question, answer,
                         embedding, tags, category, sort_order, is_active,
                         created_at, updated_at)
                    VALUES
                        ($1, $2, $3, $4, $5,
                         $6, $7, $8, $9, true,
                         $10, $10)
                    ON CONFLICT DO NOTHING
                    """,
                    uuid.uuid4(),
                    uuid.UUID(kb_id),
                    uuid.UUID(org_id),
                    row["question"],
                    row["answer"],
                    emb_np,
                    row["tags"],
                    row["category"],
                    max_order + 1 + idx,
                    now,
                )
                inserted += 1

            log.info(f"Inserted {inserted} rows into KB {kb_id}")

    finally:
        await conn.close()

    log.info("Done!")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Ingest training data into a knowledge base")
    parser.add_argument("--file",       required=True,  help="Path to Excel or CSV file")
    parser.add_argument("--kb-id",      required=True,  help="Knowledge base UUID")
    parser.add_argument("--org-id",     required=True,  help="Organization UUID")
    parser.add_argument("--clear",      action="store_true", help="Delete existing rows before inserting")
    parser.add_argument("--batch-size", type=int, default=20, help="Embedding batch size")
    args = parser.parse_args()

    asyncio.run(ingest(
        file_path=args.file,
        kb_id=args.kb_id,
        org_id=args.org_id,
        clear=args.clear,
        batch_size=args.batch_size,
    ))


if __name__ == "__main__":
    main()
