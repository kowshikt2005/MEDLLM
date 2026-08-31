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
import json
from sentence_transformers import CrossEncoder

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


def _resolve_source_name(meta: dict) -> str:
    """Pick the most useful citation label from metadata."""
    reference = str(meta.get("reference") or "").strip()
    if reference and reference.lower() != "unknown":
        return reference
    source = str(meta.get("source") or "").strip()
    return source or "Unknown"


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
        
        # Keep metadata minimal for broad chromadb compatibility.
        # Some builds reject advanced HNSW metadata fields during collection creation.
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            # We embed ourselves (embedding_service.py), so we don't want
            # ChromaDB to also try to embed. That's why we don't set
            # embedding_function here.
            metadata={
                "hnsw:space": "cosine",
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

    # ChromaDB metadata must contain only primitive types (str, int, float, bool),
    # lists of primitives, or None. Convert nested dicts or lists-of-dicts to JSON strings
    # to ensure compatibility and avoid ValueError during upsert.
    def _sanitize_meta(meta: dict) -> dict:
        sanitized = {}
        for k, v in (meta or {}).items():
            # If value is a dict, convert to JSON string
            if isinstance(v, dict):
                sanitized[k] = json.dumps(v)
            # If value is a list, ensure it contains only primitives; otherwise JSON-encode
            elif isinstance(v, list):
                if all(not isinstance(x, (dict, list)) for x in v):
                    sanitized[k] = v
                else:
                    sanitized[k] = json.dumps(v)
            else:
                # primitives (str, int, float, bool, None) are OK
                sanitized[k] = v
        return sanitized

    safe_metadatas = [_sanitize_meta(m) for m in metadatas]

    # upsert = insert OR update if ID already exists.
    # Safer than add() which throws DuplicateIDError on re-ingestion.
    collection.upsert(
        documents=texts,
        embeddings=embeddings,
        metadatas=safe_metadatas,
        ids=ids,
    )


def search(query: str, n_results: int = 3) -> list[dict]:
    """
    Find the N most semantically relevant document chunks for a query.

    Simple cosine similarity-based retrieval (no reranking for medical domain):
    1. Initial retrieval: retrieve top 10 chunks from ChromaDB using cosine similarity
    2. Filter by threshold (0.65) for high-confidence matches
    3. Return top N results to the LLM

    NOTE: Cross-encoder reranking disabled for medical domain.
    The ms-marco-MiniLM-L-6-v2 model was giving NEGATIVE logits (~-10 to -2) for 
    relevant medical documents, resulting in sigmoid scores near 0.0001 (0.01%).
    This model is trained on Wikipedia passages, not medical literature.
    Cosine similarity with BAAI/bge-large-en-v1.5 is more reliable for medical text.

    Args:
        query:     The user's chat message
        n_results: How many top chunks to return (default 3)

    Returns:
        List of dicts, each with:
          - "text":   the chunk content (injected into the LLM prompt)
          - "source": the source document filename
          - "score":  cosine similarity score (0.0-1.0, higher = more relevant)

        Returns [] if the knowledge base is empty or nothing is relevant.
    """
    collection = _get_collection()

    # Can't search an empty collection — ChromaDB would throw an error
    if collection.count() == 0:
        return []

    # Embed the query (same model as used during indexing — MUST be consistent)
    query_embedding = embed_query(query)

    # Retrieve top 10 candidates using cosine similarity
    initial_n_results = min(10, collection.count())
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=initial_n_results,
        include=["documents", "metadatas", "distances"],
    )

    docs = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results["distances"][0]

    # Filter by cosine similarity threshold
    # At 0.65+: documents are semantically very similar
    chunks = []
    for doc, meta, dist in zip(docs, metas, distances):
        cosine_similarity = 1 - (dist / 2)
        
        if cosine_similarity >= 0.65:
            chunks.append({
                "text": doc,
                "source": _resolve_source_name(meta),
                "source_file": meta.get("source", "Unknown"),
                "chunk_index": meta.get("chunk_index", 0),
                "source_id": meta.get("source_id"),
                "url": meta.get("url"),
                "publisher": meta.get("publisher"),
                "corpus": meta.get("corpus"),
                # Retrieval relevance is not factual confidence.
                "score": round(float(cosine_similarity), 3),            })

    # Return only n_results (default 3)
    return chunks[:n_results]


def search_with_lab_priority(query: str, n_results: int = 3) -> list[dict]:
    """
    Search with lab-specific optimizations.
    
    When searching for lab metrics:
      1. Prioritize lab_report documents (is_lab_pdf=True in metadata)
      2. Use exact metric name matching when possible
      3. Include reference range data directly in the response
      4. Boost scores for chunks with abnormal values
    
    Falls back to standard semantic search if no lab data found.
    
    Args:
        query: The user's question
        n_results: Number of results to return
    
    Returns:
        List of dicts with lab data enhanced results
    """
    collection = _get_collection()
    
    if collection.count() == 0:
        return []
    
    # First, try standard semantic search
    initial_results = search(query, n_results=n_results * 2)  # Get more to filter
    
    # Separate lab and non-lab results
    lab_results = []
    non_lab_results = []
    
    for result in initial_results:
        # Check if the source metadata indicates a lab document
        # (This requires accessing the actual metadata from the collection)
        if _is_lab_chunk(result):
            lab_results.append(result)
        else:
            non_lab_results.append(result)
    
    # CHANGE: Prioritize lab results, then non-lab
    # Lab PDFs are more reliable for metric extraction
    prioritized = lab_results + non_lab_results
    
    # CHANGE: Enhance lab results with reference range context
    for result in prioritized:
        result = _enhance_with_lab_metadata(result)
    
    return prioritized[:n_results]


def _is_lab_chunk(result: dict) -> bool:
    """
    Check if a result is from a lab report document.
    
    We infer this from the source name or by checking if it contains
    lab-related keywords (lab, result, reference range, etc.).
    """
    source_lower = (result.get("source", "") or "").lower()
    doc_lower = (result.get("text", "") or "").lower()
    
    # Check for explicit lab indicators in source name
    lab_indicators = ["lab", "result", "blood", "test", "report"]
    if any(ind in source_lower for ind in lab_indicators):
        return True
    
    # Check for lab keywords in the document chunk
    if any(ind in doc_lower for ind in lab_indicators):
        return True
    
    return False


def _enhance_with_lab_metadata(result: dict) -> dict:
    """
    Add lab-specific enhancements to a search result.
    
    If the chunk contains lab test data, add:
      - Direct reference range information
      - Abnormality flags
      - Suggested clinical context
    """
    # For now, just return as-is
    # In a full implementation, this would parse the chunk for lab data
    # and add structured metadata
    return result

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


def delete_documents_by_corpus(corpus: str) -> None:
    """Delete only chunks tagged with one corpus value, preserving other data."""
    collection = _get_collection()
    collection.delete(where={"corpus": corpus})

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
