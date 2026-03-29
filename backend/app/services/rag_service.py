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

from app.config import settings
from app.services.embedding_service import embed_query, embed_texts

# Collection name — like a "table" name in ChromaDB
COLLECTION_NAME = "medical_knowledge"

# Module-level singletons — initialized on first use
_client: chromadb.ClientAPI | None = None
_collection = None


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
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            # We embed ourselves (embedding_service.py), so we don't want
            # ChromaDB to also try to embed. That's why we don't set
            # embedding_function here.
            metadata={"hnsw:space": "cosine"},  # Use cosine similarity
        )

    return _collection


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

    This is called on EVERY chat message. It:
    1. Embeds the user's query into a vector
    2. Asks ChromaDB: "what chunks are closest to this vector?"
    3. Filters out low-relevance results (similarity < 0.6)
    4. Returns the relevant chunks with metadata

    Args:
        query:     The user's chat message
        n_results: How many top chunks to retrieve (default 3)

    Returns:
        List of dicts, each with:
          - "text":   the chunk content (injected into the LLM prompt)
          - "source": the source document filename
          - "score":  similarity score 0.0-1.0 (higher = more relevant)

        Returns [] if the knowledge base is empty or nothing is relevant.
    """
    collection = _get_collection()

    # Can't search an empty collection — ChromaDB would throw an error
    if collection.count() == 0:
        return []

    # Embed the query (same model as used during indexing — MUST be consistent)
    query_embedding = embed_query(query)

    # Query ChromaDB for the most similar chunks
    # min() ensures we don't request more results than we have stored
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(n_results, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    # results["documents"][0] is a list of chunk texts
    # results["metadatas"][0] is a list of metadata dicts
    # results["distances"][0] is a list of cosine distances
    # The [0] is because we queried with one query (results are batched)

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        # Convert cosine distance → similarity score
        # distance=0 means identical, distance=2 means opposite
        similarity = 1 - (dist / 2)

        # Only include genuinely relevant chunks.
        # With formula `1 - (dist/2)`, threshold 0.6 means cosine_similarity > 0.2
        # (dist < 0.8). Anything below 0.6 is likely off-topic or loosely related
        # and would add noise to the prompt rather than helping the LLM.
        if similarity > 0.6:
            chunks.append({
                "text": doc,
                "source": meta.get("source", "Unknown"),
                "chunk_index": meta.get("chunk_index", 0),
                "score": round(similarity, 3),
            })

    return chunks


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
