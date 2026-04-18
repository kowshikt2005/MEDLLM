"""
Ingest MedMCQ-style JSON explanations into ChromaDB for MEDLLM RAG.

Why this script exists:
- The default ingestion script expects document files (txt/pdf/docx/image).
- medmcq_rag_clean.json is a large structured dataset where each row has
  Topic/Explanation/Reference fields.
- This script converts each useful row into RAG-ready text blocks, chunks them,
  and stores them in ChromaDB so chat answers can retrieve explanation content.

Usage examples:
  cd backend
  venv\Scripts\activate

  # Test run on first 500 kept entries (safe dry pilot)
  python scripts/ingest_medmcq_json.py ^
    --json-path "C:\Users\kowsh\Desktop\medllama\medmcq_rag_clean.json" ^
    --max-records 500

  # Full run (append to existing collection)
  python scripts/ingest_medmcq_json.py ^
    --json-path "C:\Users\kowsh\Desktop\medllama\medmcq_rag_clean.json"

  # Full run from a clean collection
  python scripts/ingest_medmcq_json.py ^
    --json-path "C:\Users\kowsh\Desktop\medllama\medmcq_rag_clean.json" ^
    --clear-existing
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

# Add backend/ to import path (this script is in backend/scripts/)
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.document_processor import chunk_text
from app.services.rag_service import add_documents, collection_size, delete_collection

# Conservative cleaners for common mojibake seen in scraped medical text.
REPLACEMENTS = {
    "â€™": "'",
    "â€˜": "'",
    'â€œ': '"',
    'â€\x9d': '"',
    "â€“": "-",
    "â€”": "-",
    "â†’": "->",
    "Â": "",
}

# Signals that the row is mostly exam-answer formatting noise.
MCQ_NOISE_PATTERN = re.compile(
    r"\\b(Ans\\.?|Answer is|Question:|Case:)\\b|\\b[A-D]\\)",
    flags=re.IGNORECASE,
)


def clean_text(text: str) -> str:
    """Normalize whitespace and patch common mojibake artifacts."""
    cleaned = text
    for bad, good in REPLACEMENTS.items():
        cleaned = cleaned.replace(bad, good)
    cleaned = re.sub(r"\\s+", " ", cleaned).strip()
    return cleaned


def row_to_document(row: dict, row_index: int) -> str | None:
    """Convert one JSON row to a retrieval document string, or None if unusable."""
    explanation = clean_text(str(row.get("Explanation") or ""))
    topic = clean_text(str(row.get("Topic") or "General Medicine"))
    reference = clean_text(str(row.get("Reference") or "Unknown"))

    if len(explanation) < 120:
        return None

    if MCQ_NOISE_PATTERN.search(explanation):
        return None

    return (
        f"Topic: {topic}\n"
        f"Reference: {reference}\n"
        f"Explanation: {explanation}\n"
        f"Record-ID: medmcq-{row_index}"
    )


def iter_kept_documents(rows: list[dict], max_records: int | None):
    """Yield (row_index, doc_text, topic, reference) for rows that pass filtering."""
    kept = 0
    for idx, row in enumerate(rows):
        doc_text = row_to_document(row, idx)
        if not doc_text:
            continue

        topic = clean_text(str(row.get("Topic") or "General Medicine"))
        reference = clean_text(str(row.get("Reference") or "Unknown"))

        yield idx, doc_text, topic, reference
        kept += 1

        if max_records is not None and kept >= max_records:
            break


def ingest_documents(
    source_name: str,
    docs: list[tuple[int, str, str, str]],
    batch_size: int,
) -> int:
    """Chunk and ingest kept documents into ChromaDB in embedding batches."""
    texts: list[str] = []
    metadatas: list[dict] = []
    ids: list[str] = []

    for row_index, doc_text, topic, reference in docs:
        # Use a per-row source name so chunk IDs remain unique and stable.
        row_source = f"{source_name}#row_{row_index}"
        chunk_texts, chunk_metas, chunk_ids = chunk_text(
            doc_text,
            source_name=row_source,
            file_type="text",
        )

        for i in range(len(chunk_texts)):
            chunk_metas[i]["dataset"] = "medmcq"
            chunk_metas[i]["topic"] = topic
            chunk_metas[i]["reference"] = reference
            chunk_metas[i]["row_index"] = row_index

        texts.extend(chunk_texts)
        metadatas.extend(chunk_metas)
        ids.extend(chunk_ids)

    if not texts:
        return 0

    total_batches = (len(texts) - 1) // batch_size + 1
    for i in range(0, len(texts), batch_size):
        b_texts = texts[i : i + batch_size]
        b_metas = metadatas[i : i + batch_size]
        b_ids = ids[i : i + batch_size]
        add_documents(b_texts, b_metas, b_ids)
        print(f"  Stored batch {i // batch_size + 1}/{total_batches} ({len(b_texts)} chunks)")

    return len(texts)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest medmcq_rag_clean.json explanations into ChromaDB for MEDLLM RAG"
    )
    parser.add_argument(
        "--json-path",
        required=True,
        help="Absolute path to medmcq_rag_clean.json",
    )
    parser.add_argument(
        "--max-records",
        type=int,
        default=None,
        help="Optional cap on kept records (useful for pilot testing)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Embedding insert batch size (default: 100 chunks)",
    )
    parser.add_argument(
        "--clear-existing",
        action="store_true",
        help="Delete existing Chroma collection before ingesting",
    )

    args = parser.parse_args()

    json_path = Path(args.json_path)
    if not json_path.exists():
        print(f"ERROR: JSON file not found: {json_path}")
        sys.exit(1)

    print("\nMedLLM — MedMCQ JSON Ingestion")
    print("=" * 50)
    print(f"Source file: {json_path}")
    print(f"Collection size before ingest: {collection_size()} chunks")
    if args.max_records:
        print(f"Max kept records: {args.max_records}")
    print()

    if args.clear_existing:
        print("Deleting existing Chroma collection...")
        delete_collection()
        print("Collection cleared.\n")

    with open(json_path, "r", encoding="utf-8", errors="replace") as f:
        rows = json.load(f)

    if not isinstance(rows, list):
        print("ERROR: JSON root must be an array of objects.")
        sys.exit(1)

    source_name = os.path.basename(json_path)

    kept_docs = list(iter_kept_documents(rows, args.max_records))
    print(f"Rows in JSON: {len(rows)}")
    print(f"Rows kept after filtering: {len(kept_docs)}")

    if not kept_docs:
        print("No rows passed filtering. Nothing ingested.")
        return

    chunk_count = ingest_documents(source_name, kept_docs, args.batch_size)

    print("\n" + "=" * 50)
    print("Ingestion complete")
    print(f"Chunks added/updated: {chunk_count}")
    print(f"Collection size after ingest: {collection_size()} chunks")
    print("Next: restart backend (if running) and ask test medical questions in chat.")


if __name__ == "__main__":
    main()
