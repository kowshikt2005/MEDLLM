"""
Embedding service — converts text into vectors using sentence-transformers.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHAT IS AN EMBEDDING?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
An embedding is a list of floating-point numbers (a "vector") that
represents the *meaning* of a piece of text — not just its words.

Example (simplified to 3 dimensions instead of 384):
  "heart attack symptoms"   → [0.91, -0.12, 0.47]
  "myocardial infarction"   → [0.89, -0.10, 0.49]  ← very similar!
  "how to bake a cake"      → [-0.34, 0.77, -0.65] ← very different

The model learned these relationships from massive amounts of text.
It knows "heart attack" and "myocardial infarction" mean the same thing
because they appear in similar contexts in medical literature.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHY all-MiniLM-L6-v2?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This model produces 384-dimensional vectors. It's:
  - Small (80MB download, already in config.py as the default)
  - Fast — runs well on CPU (no GPU needed)
  - Good quality for general semantic similarity
  - Open source, free, no API key required

It's already defined in config.py as `embedding_model = "all-MiniLM-L6-v2"`.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LAZY LOADING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
We don't load the model when the module is imported. We load it on the
FIRST actual call to embed_texts() or embed_query(). This keeps server
startup fast — the model only loads when it's actually needed.

After the first load, it stays in memory for all subsequent calls
(because _model is module-level, it persists between requests).
"""

from sentence_transformers import SentenceTransformer

from app.config import settings

# Module-level singleton — None until first use
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """
    Lazy-load the embedding model on first call.

    The `global` keyword tells Python we're modifying the module-level
    _model variable (not creating a new local variable named _model).
    """
    global _model
    if _model is None:
        print(f"[Embedding] Loading model: {settings.embedding_model} (first-time ~2s)...")
        _model = SentenceTransformer(settings.embedding_model)
        print("[Embedding] Model loaded and cached in memory.")
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Convert a list of text strings into embedding vectors.

    Used during INDEXING — when we add documents to ChromaDB.
    We embed all chunks at once (batch) because it's much faster
    than embedding them one at a time.

    Args:
        texts: e.g. ["Diabetes is a metabolic disease...", "Insulin regulates blood sugar..."]

    Returns:
        A list of vectors. Each vector is a list of 384 floats.
        e.g. [[0.12, -0.45, 0.87, ...], [0.34, 0.21, -0.66, ...]]

    The returned list has the same length as the input list — one vector per text.
    """
    model = _get_model()
    # show_progress_bar=False keeps logs clean during web requests
    embeddings = model.encode(texts, show_progress_bar=False)
    # .tolist() converts numpy arrays to plain Python lists (required for ChromaDB)
    return embeddings.tolist()


def embed_query(query: str) -> list[float]:
    """
    Convert a single query string into an embedding vector.

    Used at QUERY TIME — when a user sends a message and we need to
    find the most relevant document chunks.

    Args:
        query: e.g. "What are the symptoms of type 2 diabetes?"

    Returns:
        A single vector (list of 384 floats).
    """
    model = _get_model()
    # We pass a list with one item, then take [0] to get just that item's vector
    embeddings = model.encode([query], show_progress_bar=False)
    return embeddings[0].tolist()
