"""
RAG service — stores and retrieves document chunks using ChromaDB.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHAT IS ChromaDB?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ChromaDB is a "vector database" — a database specifically designed to
store embedding vectors and find similar ones FAST.

Normal SQL databases store rows of data and answer questions like:
  "Give me all users whose age > 30"

ChromaDB answers questions like:
  "Give me the 3 text chunks whose meaning is most similar to this query"

It does this using approximate nearest-neighbor (ANN) search, which is
like finding the 3 closest points in 384-dimensional space.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COSINE SIMILARITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
We use cosine similarity to measure how "close" two vectors are.
Cosine similarity measures the angle between two vectors:
  - Score of 1.0 = same direction = identical meaning
  - Score of 0.0 = perpendicular = unrelated
  - Score of -1.0 = opposite directions = opposite meaning

ChromaDB returns cosine DISTANCE (0 = identical, 2 = opposite).
We convert to similarity with: similarity = 1 - (distance / 2)
This maps the [0, 2] distance range to a [1, 0] similarity range.
We then threshold at 0.6 to only use genuinely relevant chunks.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PERSISTENT STORAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ChromaDB with PersistentClient stores data to disk at chroma_persist_dir.
You run the ingestion script ONCE to build the index. Then every server
restart reads the same data — no need to re-index every time.
"""

import chromadb
from cross_encoder import CrossEncoder

from app.config import settings
from app.services.embedding_service import embed_query, embed_texts

# Collection name — like a "table" name in ChromaDB
COLLECTION_NAME = "medical_knowledge"

# CHANGE: Add cross-encoder reranker for Top-K reranking
# This model is specifically designed for ranking search results
# "ms-marco-MiniLM-L-6-v2" is optimized for semantic relevance ranking
RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# Module-level singletons — initialized on first use
_client: chromadb.ClientAPI | None = None
_collection = None
_reranker: CrossEncoder | None = None


def _get_collection():
    """
    Get or create the ChromaDB collection, connecting to persistent storage.

    A "collection" in ChromaDB is like a table — it groups related documents.
    We use ONE collection for all medical knowledge base documents.

    PersistentClient saves data to disk so it survives server restarts.
    get_or_create_collection either loads an existing collection or makes a new one.
    """
    global _client, _collection

    if _collection is None:
        # PersistentClient saves the index to disk at chroma_persist_dir.
        # No extra settings needed — chromadb 0.5.x works cleanly without them.
        _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        
        # CHANGE: Updated HNSW configuration for improved retrieval quality
        # hnsw:M = 48 (increased from default 5) - more connections per node = better recall
        # hnsw:ef_construction = 200 (increased from default 200) - better index construction
        # These parameters improve search accuracy at the cost of slightly longer construction time
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            # We embed ourselves (embedding_service.py), so we don't want
            # ChromaDB to also try to embed. That's why we don't set
            # embedding_function here.
            metadata={
                "hnsw:space": "cosine",
                "hnsw:M": 48,
                "hnsw:ef_construction": 200,
            },
        )

    return _collection


# CHANGE: New function to get/load the cross-encoder reranker model
def _get_reranker() -> CrossEncoder:
    """
    Lazy-load the cross-encoder model on first call.
    
    The cross-encoder model is used to rerank the top-K results from ChromaDB.
    It's more accurate than cosine similarity but slower, so we use it after
    the initial fast similarity search (Top-K reranking approach).
    
    Lazy loading keeps server startup fast — the model only loads when needed.
    """
    global _reranker
    if _reranker is None:
        print(f"[Reranker] Loading model: {RERANKER_MODEL_NAME} (first-time ~3-5s)...")
        _reranker = CrossEncoder(RERANKER_MODEL_NAME)
        print("[Reranker] Model loaded and cached in memory.")
    return _reranker


def add_documents(
    texts: list[str],
    metadatas: list[dict],
    ids: list[str],
) -> None:
    """
    Add document chunks to ChromaDB.

    This is called by the ingestion script (scripts/ingest_knowledge_base.py).
    It's NOT called during normal chat — only when building the knowledge base.

    Args:
        texts:     List of text chunks. e.g. ["Diabetes is a condition...", ...]
        metadatas: One dict per chunk. e.g. [{"source": "diabetes.pdf", "chunk_index": 0}, ...]
        ids:       Unique string ID per chunk. e.g. ["diabetes_chunk_0_abc123", ...]

    Why provide IDs manually?
        ChromaDB requires unique IDs. If you re-ingest the same document,
        using the same IDs causes an error instead of creating duplicates.
        Our ingestion script generates stable IDs based on content hashes.
    """
    collection = _get_collection()

    # Embed all texts in one batch (much faster than one at a time)
    embeddings = embed_texts(texts)

    # upsert = insert OR update if ID already exists.
    # Safer than add() which throws DuplicateIDError on re-ingestion.
    collection.upsert(
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids,
    )


def search(query: str, n_results: int = 3) -> list[dict]:
    """
    Find the N most semantically relevant document chunks for a query.

    This implements Top-K Rerank RAG for improved relevance:
    1. Initial retrieval: retrieve top 15 chunks from ChromaDB using cosine similarity
    2. Reranking: apply cross-encoder model to get more accurate relevance scores
    3. Selection: pick the top 5 after reranking
    4. Filtering: apply cosine similarity threshold (0.6) to remove low-relevance chunks
    5. Return: top N results (default 3) to the LLM

    CHANGE: Implements Top-K reranking strategy for better result quality
    This retrieves more candidates initially, then uses a more accurate cross-encoder
    to rerank them, improving the relevance of final results.

    Args:
        query:     The user's chat message
        n_results: How many top chunks to return (default 3, max 5 after reranking)

    Returns:
        List of dicts, each with:
          - "text":   the chunk content (injected into the LLM prompt)
          - "source": the source document filename
          - "score":  cross-encoder relevance score (0.0-1.0, higher = more relevant)

        Returns [] if the knowledge base is empty or nothing is relevant.
    """
    collection = _get_collection()

    # Can't search an empty collection — ChromaDB would throw an error
    if collection.count() == 0:
        return []

    # Embed the query (same model as used during indexing — MUST be consistent)
    query_embedding = embed_query(query)

    # ── STAGE 1: Initial retrieval ──────────────────────────────────────────
    # CHANGE: Retrieve top 15 candidates (instead of just n_results)
    # This gives the reranker more options to work with
    initial_n_results = min(15, collection.count())
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=initial_n_results,
        include=["documents", "metadatas", "distances"],
    )

    docs = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results["distances"][0]

    # ── STAGE 2: Cross-encoder reranking ────────────────────────────────────
    # CHANGE: Apply reranker to get more accurate relevance scores
    # Build query-document pairs for the reranker
    candidate_pairs = [[query, doc] for doc in docs]
    
    try:
        reranker = _get_reranker()
        # Cross-encoder returns scores for each pair (0-1, higher = more relevant)
        reranker_scores = reranker.predict(candidate_pairs)
        
        # Create list of (index, score) tuples and sort by reranker score
        indexed_scores = list(enumerate(reranker_scores))
        indexed_scores.sort(key=lambda x: x[1], reverse=True)
        
        # ── STAGE 3: Select top 5 after reranking ───────────────────────────
        # CHANGE: Keep top 5 reranked results
        top_k_after_rerank = 5
        selected_indices = [idx for idx, _ in indexed_scores[:top_k_after_rerank]]
        
    except Exception as e:
        # Fallback if reranker fails — use original cosine distances
        print(f"[RAG] Reranker error: {e}. Falling back to cosine similarity scores.")
        selected_indices = list(range(len(docs)))
        reranker_scores = [1 - (dist / 2) for dist in distances]  # Convert to similarity

    # ── STAGE 4: Filter by cosine similarity and format results ────────────
    chunks = []
    for idx in selected_indices:
        if idx >= len(docs):
            continue
            
        doc = docs[idx]
        meta = metas[idx]
        dist = distances[idx]

        # Convert cosine distance → similarity score
        # distance=0 means identical, distance=2 means opposite
        similarity = 1 - (dist / 2)

        # CHANGE: Keep original cosine similarity filtering
        # Only include results with similarity > 0.6 (genuinely relevant)
        # This threshold removes off-topic or loosely related chunks
        if similarity > 0.6:
            # Get reranker score if available, otherwise use similarity
            reranker_score = reranker_scores[idx] if idx < len(reranker_scores) else similarity
            
            chunks.append({
                "text": doc,
                "source": meta.get("source", "Unknown"),
                "chunk_index": meta.get("chunk_index", 0),
                "score": round(float(reranker_score), 3),  # CHANGE: Use reranker score
            })

    # Return only n_results (default 3, but limited by what passed filtering)
    return chunks[:n_results]


def collection_size() -> int:
    """
    Return the number of document chunks currently in ChromaDB.

    Returns 0 on any error (e.g. ChromaDB not yet initialized).
    This is called by the ingestion script to report progress.
    """
    try:
        return _get_collection().count()
    except Exception:
        return 0


def delete_collection() -> None:
    """
    Delete ALL documents in the collection.

    Used by the ingestion script when re-indexing from scratch.
    After deletion, the next call to _get_collection() will create
    a fresh empty collection.
    """
    global _client, _collection
    if _client:
        _client.delete_collection(COLLECTION_NAME)
        _collection = None  # Force re-creation on next access
