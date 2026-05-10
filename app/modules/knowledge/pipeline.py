"""
Knowledge Base — RAG Pipeline.
Handles: chunking → embedding → storage → hybrid search.
All embedding calls route through the configured AI provider.
"""

import hashlib
import logging
import re
from typing import List, Optional, Tuple
from uuid import UUID

# ── In-process embedding cache ─────────────────────────────────────────────────
# Keyed by (model_id, sha256(text[:200])). Survives for the server lifetime.
# Saves one Ollama round-trip (~300-700 ms) for repeated or similar queries.
_EMBED_CACHE: dict = {}
_EMBED_CACHE_MAX = 2000  # ~2 000 vectors × 768 floats × 4 bytes ≈ 6 MB

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge.models import (
    KnowledgeChunk, KnowledgeDocument, KnowledgeQAPair,
    DocumentStatus, VECTOR_AVAILABLE
)
from app.modules.knowledge.repository import (
    ChunkRepository, DocumentRepository, QAPairRepository
)
from app.modules.knowledge.schemas import RAGSearchResult
from app.modules.tokens.models import TokenAction
from app.modules.tokens.schemas import DebitTokensRequest

logger = logging.getLogger(__name__)

# ── Chunking Config ────────────────────────────────────────────────────────────
CHUNK_SIZE          = 512      # target tokens per chunk
CHUNK_OVERLAP       = 64       # token overlap between chunks
MAX_CHUNK_CHARS     = 2000     # hard char limit per chunk
EMBEDDING_DIM       = 768      # nomic-embed-text


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split text into overlapping chunks at sentence boundaries.
    Returns list of chunk strings.
    """
    # Rough: ~4 chars per token
    char_size = chunk_size * 4
    char_overlap = overlap * 4

    # Split at sentence boundaries first
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= char_size:
            current = (current + " " + sentence).strip()
        else:
            if current:
                chunks.append(current[:MAX_CHUNK_CHARS])
            # Start new chunk with overlap from end of previous
            if current:
                overlap_text = current[-char_overlap:] if len(current) > char_overlap else current
                current = (overlap_text + " " + sentence).strip()
            else:
                current = sentence

    if current:
        chunks.append(current[:MAX_CHUNK_CHARS])

    return [c for c in chunks if c.strip()]


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return max(1, len(text) // 4)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class EmbeddingClient:
    """
    Thin wrapper around the configured embedding provider.
    Supports Ollama (nomic-embed-text), OpenAI (text-embedding-3-small), etc.
    """

    def __init__(self, provider_config: dict):
        self.config = provider_config

    async def embed(self, texts: List[str]) -> List[List[float]]:
        provider_type = self.config.get("provider_type", "ollama")
        api_key       = self.config.get("api_key")
        base_url      = self.config.get("base_url", "http://localhost:11434")
        model_id      = self.config.get("model_id", "nomic-embed-text")

        # ── Cache lookup ───────────────────────────────────────────────────────
        results = [None] * len(texts)
        uncached_indices = []
        uncached_texts   = []
        for i, text in enumerate(texts):
            key = hashlib.sha256(f"{model_id}:{text[:300]}".encode()).hexdigest()
            if key in _EMBED_CACHE:
                results[i] = _EMBED_CACHE[key]
            else:
                uncached_indices.append(i)
                uncached_texts.append((i, key, text))

        if uncached_texts:
            raw_texts = [t for _, _, t in uncached_texts]
            if provider_type == "ollama":
                fresh = await self._embed_ollama(raw_texts, base_url, model_id)
            elif provider_type == "openai":
                fresh = await self._embed_openai(raw_texts, api_key, model_id)
            else:
                logger.warning(f"Unsupported embedding provider: {provider_type}. Returning zero vectors.")
                fresh = [[0.0] * EMBEDDING_DIM for _ in raw_texts]

            for (orig_i, key, _), vec in zip(uncached_texts, fresh):
                results[orig_i] = vec
                # Store in cache; evict oldest if over limit
                if len(_EMBED_CACHE) >= _EMBED_CACHE_MAX:
                    oldest = next(iter(_EMBED_CACHE))
                    del _EMBED_CACHE[oldest]
                _EMBED_CACHE[key] = vec

        return results

    async def _embed_ollama(self, texts: List[str], base_url: str, model: str) -> List[List[float]]:
        import httpx
        results = []
        async with httpx.AsyncClient(timeout=60) as client:
            for text in texts:
                try:
                    resp = await client.post(
                        f"{base_url}/api/embeddings",
                        json={"model": model, "prompt": text},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    emb = data.get("embedding", [0.0] * EMBEDDING_DIM)
                    # Pad or truncate to EMBEDDING_DIM
                    if len(emb) < EMBEDDING_DIM:
                        emb = emb + [0.0] * (EMBEDDING_DIM - len(emb))
                    results.append(emb[:EMBEDDING_DIM])
                except Exception as e:
                    logger.error(f"Ollama embed error: {e}")
                    results.append([0.0] * EMBEDDING_DIM)
        return results

    async def _embed_openai(self, texts: List[str], api_key: str, model: str) -> List[List[float]]:
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=api_key)
            resp = await client.embeddings.create(input=texts, model=model)
            return [item.embedding for item in resp.data]
        except Exception as e:
            logger.error(f"OpenAI embed error: {e}")
            return [[0.0] * EMBEDDING_DIM for _ in texts]


class RAGPipeline:
    """
    Core RAG pipeline:
    1. ingest_document(doc_id) — chunk → embed → store
    2. search(kb_id, query) — embed query → HNSW search → ranked results
    """

    def __init__(self, db: AsyncSession, embedding_config: Optional[dict] = None):
        self.db         = db
        self.docs       = DocumentRepository(db)
        self.chunks     = ChunkRepository(db)
        self.qa_pairs   = QAPairRepository(db)
        self.embedder   = EmbeddingClient(embedding_config or {
            "provider_type": "ollama",
            "base_url": "http://localhost:11434",
            "model_id": "nomic-embed-text",
        })

    # ── Ingest ─────────────────────────────────────────────────────────────────

    async def ingest_document(self, doc_id: UUID, org_id: UUID) -> int:
        """
        Process a document: chunk the raw_content, embed each chunk, store.
        Returns number of chunks created.
        """
        doc = await self.docs.get_by_id(doc_id)
        if not doc or not doc.raw_content:
            await self.docs.update_status(doc_id, DocumentStatus.failed,
                                          error_message="No raw content to process")
            return 0

        await self.docs.update_status(doc_id, DocumentStatus.processing)

        try:
            text = doc.raw_content.strip()
            chunk_texts = chunk_text(text)

            if not chunk_texts:
                await self.docs.update_status(doc_id, DocumentStatus.failed,
                                              error_message="No text chunks produced")
                return 0

            # Embed all chunks in one batch
            embeddings = await self.embedder.embed(chunk_texts)

            # Delete old chunks if re-ingesting
            await self.chunks.delete_for_document(doc_id)

            new_chunks = []
            for i, (chunk_content, embedding) in enumerate(zip(chunk_texts, embeddings)):
                chunk = KnowledgeChunk(
                    document_id=doc.id,
                    knowledge_base_id=doc.knowledge_base_id,
                    org_id=org_id,
                    content=chunk_content,
                    chunk_index=i,
                    token_count=estimate_tokens(chunk_content),
                    metadata={"doc_title": doc.title, "chunk_of": len(chunk_texts)},
                )
                if VECTOR_AVAILABLE and embedding:
                    chunk.embedding = embedding
                new_chunks.append(chunk)

            await self.chunks.bulk_create(new_chunks)
            await self.docs.update_status(doc_id, DocumentStatus.indexed,
                                          chunk_count=len(new_chunks))

            logger.info(f"Ingested doc {doc_id}: {len(new_chunks)} chunks")
            return len(new_chunks)

        except Exception as e:
            logger.error(f"Ingest error for doc {doc_id}: {e}")
            await self.docs.update_status(doc_id, DocumentStatus.failed,
                                          error_message=str(e)[:500])
            return 0

    async def embed_qa_pair(self, qa_id: UUID, org_id: UUID) -> bool:
        """Embed a Q&A pair's question for semantic retrieval."""
        qa = await self.qa_pairs.get_by_id(qa_id, org_id)
        if not qa:
            return False
        try:
            embeddings = await self.embedder.embed([qa.question])
            if embeddings and VECTOR_AVAILABLE:
                await self.qa_pairs.update(qa_id, org_id, embedding=embeddings[0])
            return True
        except Exception as e:
            logger.error(f"QA embed error for {qa_id}: {e}")
            return False

    async def embed_qa_pairs_batch(
        self, qa_pairs: list, org_id: UUID, batch_size: int = 30
    ) -> int:
        """Batch-embed a list of KnowledgeQAPair objects. Returns count embedded."""
        if not VECTOR_AVAILABLE:
            return 0
        embedded = 0
        for i in range(0, len(qa_pairs), batch_size):
            batch = qa_pairs[i:i + batch_size]
            texts = [qa.question for qa in batch]
            try:
                embeddings = await self.embedder.embed(texts)
                for qa, emb in zip(batch, embeddings):
                    if emb:
                        await self.qa_pairs.update(qa.id, org_id, embedding=emb)
                        embedded += 1
            except Exception as e:
                logger.error(f"Batch embed error at batch {i}: {e}")
        return embedded

    # ── Search ─────────────────────────────────────────────────────────────────

    async def search(
        self,
        kb_id: UUID,
        query: str,
        top_k: int = 5,
        threshold: float = 0.5,
    ) -> List[RAGSearchResult]:
        """
        Hybrid search:
        1. Check Q&A pairs first (higher threshold — direct match)
        2. Fall back to chunk vector search
        Returns ranked, deduplicated results.
        """
        query_embeddings = await self.embedder.embed([query])
        if not query_embeddings:
            return []

        query_embedding = query_embeddings[0]
        results: List[RAGSearchResult] = []

        # 1. Q&A pairs (threshold = max(0.85, threshold))
        qa_threshold = max(0.6, threshold)
        qa_hits = await self.qa_pairs.vector_search(
            kb_id, query_embedding, top_k=3, threshold=qa_threshold
        )
        for qa, score in qa_hits:
            results.append(RAGSearchResult(
                chunk_id=qa.id,
                document_id=qa.id,   # reuse field — QA pairs are self-contained
                content=f"Q: {qa.question}\nA: {qa.answer}",
                score=score,
                metadata={"type": "qa_pair", "tags": qa.tags or []},
                source_type="qa_pair",
            ))

        # 2. Chunk search
        remaining = top_k - len(results)
        if remaining > 0:
            chunk_hits = await self.chunks.vector_search(
                kb_id, query_embedding, top_k=remaining, threshold=threshold
            )
            for chunk, score in chunk_hits:
                results.append(RAGSearchResult(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    content=chunk.content,
                    score=score,
                    metadata=chunk.metadata or {},
                    source_type="chunk",
                ))

        # Sort by score descending
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    async def search_multi_kb(
        self,
        kb_ids: List[UUID],
        query: str,
        top_k: int = 5,
        threshold: float = 0.5,
    ) -> List[RAGSearchResult]:
        """
        Search across multiple knowledge bases and merge results.
        Deduplicates by content hash and returns top_k by score.
        """
        if not kb_ids:
            return []
        if len(kb_ids) == 1:
            return await self.search(kb_ids[0], query, top_k, threshold)

        # Embed once, search all KBs
        query_embeddings = await self.embedder.embed([query])
        if not query_embeddings:
            return []
        query_embedding = query_embeddings[0]

        all_results: List[RAGSearchResult] = []
        seen_content: set = set()

        for kb_id in kb_ids:
            qa_threshold = max(0.6, threshold)
            qa_hits = await self.qa_pairs.vector_search(
                kb_id, query_embedding, top_k=top_k, threshold=qa_threshold
            )
            for qa, score in qa_hits:
                key = hashlib.sha256(qa.answer.encode()[:100]).hexdigest()
                if key not in seen_content:
                    seen_content.add(key)
                    all_results.append(RAGSearchResult(
                        chunk_id=qa.id,
                        document_id=qa.id,
                        content=f"Q: {qa.question}\nA: {qa.answer}",
                        score=score,
                        metadata={"type": "qa_pair", "tags": qa.tags or [], "kb_id": str(kb_id)},
                        source_type="qa_pair",
                    ))

            chunk_hits = await self.chunks.vector_search(
                kb_id, query_embedding, top_k=top_k, threshold=threshold
            )
            for chunk, score in chunk_hits:
                key = hashlib.sha256(chunk.content.encode()[:100]).hexdigest()
                if key not in seen_content:
                    seen_content.add(key)
                    all_results.append(RAGSearchResult(
                        chunk_id=chunk.id,
                        document_id=chunk.document_id,
                        content=chunk.content,
                        score=score,
                        metadata={**(chunk.metadata or {}), "kb_id": str(kb_id)},
                        source_type="chunk",
                    ))

        all_results.sort(key=lambda r: r.score, reverse=True)
        return all_results[:top_k]

    def build_context(self, results: List[RAGSearchResult], max_chars: int = 4000) -> str:
        """
        Concatenate search results into a context string for LLM injection.
        Respects max_chars to stay within context window.
        Q&A pairs are formatted to surface the answer clearly.
        """
        parts = []
        total = 0
        for i, r in enumerate(results):
            # For Q&A pairs, present as clear fact with topic context
            if r.source_type == "qa_pair" and r.content.startswith("Q:"):
                lines = r.content.split("\nA:", 1)
                question_part = lines[0][2:].strip()   # strip leading "Q:"
                answer_part   = lines[1].strip() if len(lines) > 1 else r.content
                content = f"[Fact {i+1}] Topic: {question_part}\nAnswer: {answer_part}"
            else:
                content = f"[Source {i+1}]\n{r.content}"
            snippet = content + "\n"
            if total + len(snippet) > max_chars:
                break
            parts.append(snippet)
            total += len(snippet)
        return "\n---\n".join(parts)
