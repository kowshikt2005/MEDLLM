"""
Knowledge base ingestion script.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHAT THIS SCRIPT DOES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Reads all documents in backend/data/knowledge_base/
2. Extracts text from each file (PDF, DOCX, TXT — same as Phase 2)
3. CHANGE: Splits text into chunks using file-type aware sizing:
   - PDF: 1200 chars, 200 overlap (structured content)
   - DOCX: 1000 chars, 150 overlap (narrative)
   - Text/CSV/MD: 800 chars, 120 overlap (dense)
4. Embeds each chunk using sentence-transformers (all-MiniLM-L6-v2)
5. Stores the chunks + embeddings in ChromaDB (persistent on disk)

Run ONCE before starting the server (or whenever you add new documents):
  cd backend
  venv\Scripts\activate   (Windows)
  python scripts/ingest_knowledge_base.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHAT IS CHUNKING?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A medical textbook might be 500,000 characters. We can't embed that as
a single piece — it would take too much memory and the resulting vector
would be a blurry average of everything.

Instead, we split it into chunks with OVERLAP between consecutive chunks.
The overlap prevents important information from being cut in half at a
chunk boundary.

CHANGE: Chunk sizes now depend on file type:
- PDFs (1200 chars): Benefit from larger chunks due to structured content
- DOCX (1000 chars): Narrative documents with medium density
- Text files (800 chars): Often dense, use smaller chunks for precision
- Image OCR (700 chars): Less reliable, smaller chunks for safety

Example with CHUNK_SIZE=20, CHUNK_OVERLAP=5:
  "Diabetes is a chronic disease that affects blood sugar levels"
  chunk 0: "Diabetes is a chroni"
  chunk 1: "chroni c disease that"    ← "chroni" repeated as overlap
  chunk 2: "t affects blood sugar"    ← "t" from "that" repeated
  chunk 3: "sugar levels"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STABLE IDs
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
We generate each chunk's ID from a hash of its content.
This means:
  - Re-running the script on the SAME files generates the SAME IDs
  - ChromaDB can detect and skip already-indexed chunks
  - No random UUIDs that change every run
"""

import asyncio
import os
import sys

# ── Add backend/ to Python path ───────────────────────────────────────────────
# This script lives in backend/scripts/ but imports from backend/app/.
# We need to tell Python where to find the app package.
# os.path.dirname(__file__)                      → backend/scripts/
# os.path.dirname(os.path.dirname(__file__))     → backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.document_processor import detect_file_type, extract_text, chunk_text
from app.services.rag_service import add_documents, collection_size, delete_collection

# ── Configuration ─────────────────────────────────────────────────────────────
KNOWLEDGE_BASE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "knowledge_base",
)

# CHANGE: File-type aware chunking is now handled by document_processor.chunk_text()
# See CHUNK_CONFIG in document_processor.py for per-file-type settings:
#   - PDF: 1200 chars, 200 overlap
#   - DOCX: 1000 chars, 150 overlap
#   - Text/CSV/MD: 800 chars, 120 overlap
#   - Image: 700 chars, 100 overlap

BATCH_SIZE = 50      # How many chunks to add to ChromaDB at once


# ── Single-file processing ────────────────────────────────────────────────────

async def ingest_file(file_path: str, filename: str) -> int:
    """
    Process one file: extract → chunk → embed → store in ChromaDB.

    CHANGE: Uses file-type aware chunking with optimized sizes per file type

    Returns the number of chunks added (0 if skipped).
    """
    file_type = detect_file_type(filename)

    if file_type == "unknown":
        print(f"    Skipping {filename}: unsupported file type")
        return 0

    print(f"    Extracting text...")
    text = await extract_text(file_path, file_type)

    if not text or len(text.strip()) < 50:
        print(f"    Skipping {filename}: no usable text extracted")
        return 0

    print(f"    {len(text)} characters extracted. Chunking with {file_type} parameters...")
    # CHANGE: Pass file_type to chunk_text for type-aware chunking
    texts, metadatas, ids = chunk_text(text, filename, file_type=file_type)
    print(f"    {len(texts)} chunks created ({metadatas[0]['file_type']} config). Embedding + storing...")

    # Add in batches to avoid loading all embeddings into memory at once
    for i in range(0, len(texts), BATCH_SIZE):
        batch_texts = texts[i : i + BATCH_SIZE]
        batch_metas = metadatas[i : i + BATCH_SIZE]
        batch_ids = ids[i : i + BATCH_SIZE]
        add_documents(batch_texts, batch_metas, batch_ids)
        print(f"    Batch {i // BATCH_SIZE + 1}/{(len(texts) - 1) // BATCH_SIZE + 1} stored.")

    return len(texts)


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    print()
    print("MedLLM — Knowledge Base Ingestion")
    print("=" * 50)
    print(f"Directory: {KNOWLEDGE_BASE_DIR}")
    # CHANGE: Show that chunking is now file-type aware
    print(f"Chunking: File-type aware (PDF: 1200/200, DOCX: 1000/150, Text: 800/120, Image: 700/100)")
    print()

    # Verify the knowledge base directory exists
    if not os.path.exists(KNOWLEDGE_BASE_DIR):
        print(f"ERROR: Directory not found: {KNOWLEDGE_BASE_DIR}")
        print("Create the directory and add medical documents (PDF, DOCX, TXT) to it.")
        return

    # List all files (skip hidden files like .DS_Store)
    files = [
        f for f in os.listdir(KNOWLEDGE_BASE_DIR)
        if os.path.isfile(os.path.join(KNOWLEDGE_BASE_DIR, f))
        and not f.startswith(".")
    ]

    if not files:
        print("No files found in knowledge base directory.")
        print(f"Add medical documents (PDF, DOCX, TXT) to:\n  {KNOWLEDGE_BASE_DIR}")
        return

    print(f"Found {len(files)} file(s):")
    for f in files:
        print(f"  - {f}")
    print()

    # If ChromaDB already has data, ask before overwriting
    existing = collection_size()
    if existing > 0:
        print(f"WARNING: ChromaDB already contains {existing} chunks.")
        answer = input("Delete existing data and re-index everything? (y/N): ").strip().lower()
        if answer == "y":
            print("Deleting existing collection...")
            delete_collection()
            print("Deleted. Starting fresh.\n")
        else:
            print("Appending to existing collection.")
            print("NOTE: Re-ingesting the same files will cause duplicate errors.")
            print("      Delete data/chroma_db/ manually to start completely fresh.\n")

    # Process each file
    total_chunks = 0
    for filename in files:
        file_path = os.path.join(KNOWLEDGE_BASE_DIR, filename)
        print(f"Processing: {filename}")
        count = await ingest_file(file_path, filename)
        total_chunks += count
        if count > 0:
            print(f"    ✓ {count} chunks added\n")

    # Final summary
    print("=" * 50)
    print(f"Ingestion complete!")
    print(f"Total chunks in ChromaDB: {collection_size()}")
    print()
    print("Next steps:")
    print("  1. Start the backend: uvicorn app.main:app --reload")
    print("  2. Ask a medical question — the LLM will now cite sources!")


if __name__ == "__main__":
    asyncio.run(main())
