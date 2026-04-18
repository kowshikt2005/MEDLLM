r"""
Ingest MedMCQ explanation JSON into ChromaDB as structured RAG documents.

This script is designed for datasets like:
  C:\Users\kowsh\Desktop\medllama\medmcq_rag_clean.json

Each JSON row becomes one searchable document in ChromaDB with this shape:
  Topic: ...
  Explanation: ...
  Reference: ...

Why this script exists:
- Ingesting raw JSON as plain text creates noisy chunks.
- Here we index only useful explanation-centric content.
- This improves retrieval quality for question analysis in chat.

Usage examples:
  cd backend
  venv\Scripts\activate

  # Preview counts without writing to ChromaDB
  python scripts/ingest_medmcq_explanations.py --dry-run

  # Ingest with defaults
  python scripts/ingest_medmcq_explanations.py

  # Ingest a custom file and clear existing collection first
  python scripts/ingest_medmcq_explanations.py --json-path "C:\\path\\to\\medmcq_rag_clean.json" --clear-existing
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

# Add backend/ to Python path so imports from app.* work when script is run directly.
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.services.rag_service import add_documents, collection_size, delete_collection

DEFAULT_JSON_PATH = Path(r"C:\Users\kowsh\Desktop\medllama\medmcq_rag_clean.json")
DEFAULT_BATCH_SIZE = 128


def normalize_text(text: str) -> str:
    """Normalize whitespace and trim noisy separators."""
    text = text.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def looks_like_mcq_noise(text: str) -> bool:
    """Detect MCQ-answer style boilerplate that hurts retrieval quality."""
    return bool(re.search(r"\b(Ans\.|Answer is|A\)|B\)|C\)|D\)|Question:|Case:)\b", text, re.IGNORECASE))


def build_document(topic: str, explanation: str, reference: str) -> str:
    """Create structured text block for embedding and retrieval."""
    return (
        f"Topic: {topic}\n"
        f"Explanation: {explanation}\n"
        f"Reference: {reference}"
    )


def parse_records(
    json_path: Path,
    min_explanation_len: int,
    max_explanation_len: int,
    skip_unknown_reference: bool,
    skip_mcq_style: bool,
) -> tuple[list[str], list[dict], list[str], dict[str, int]]:
    """
    Parse and filter JSON rows into documents + metadata + stable IDs.

    Returns:
      texts, metadatas, ids, stats
    """
    with json_path.open("r", encoding="utf-8", errors="replace") as f:
        raw = json.load(f)

    if not isinstance(raw, list):
        raise ValueError("Expected top-level JSON array of objects.")

    texts: list[str] = []
    metadatas: list[dict] = []
    ids: list[str] = []

    stats = {
        "total_rows": len(raw),
        "kept": 0,
        "skip_missing_explanation": 0,
        "skip_too_short": 0,
        "skip_too_long": 0,
        "skip_unknown_reference": 0,
        "skip_mcq_style": 0,
    }

    source_name = json_path.name

    for idx, row in enumerate(raw):
        if not isinstance(row, dict):
            stats["skip_missing_explanation"] += 1
            continue

        explanation = normalize_text(str(row.get("Explanation", "")))
        if not explanation:
            stats["skip_missing_explanation"] += 1
            continue

        if len(explanation) < min_explanation_len:
            stats["skip_too_short"] += 1
            continue

        if len(explanation) > max_explanation_len:
            stats["skip_too_long"] += 1
            continue

        if skip_mcq_style and looks_like_mcq_noise(explanation):
            stats["skip_mcq_style"] += 1
            continue

        topic = normalize_text(str(row.get("Topic") or "General medicine"))
        reference = normalize_text(str(row.get("Reference") or "Unknown"))

        if skip_unknown_reference and reference.lower() == "unknown":
            stats["skip_unknown_reference"] += 1
            continue

        doc = build_document(topic=topic, explanation=explanation, reference=reference)

        stable_hash = hashlib.md5(f"{idx}:{topic}:{explanation}".encode("utf-8")).hexdigest()[:10]
        chunk_id = f"medmcq_row_{idx}_{stable_hash}"

        texts.append(doc)
        metadatas.append(
            {
                "source": source_name,
                "dataset": "medmcq",
                "row_index": idx,
                "topic": topic,
                "reference": reference,
            }
        )
        ids.append(chunk_id)
        stats["kept"] += 1

    return texts, metadatas, ids, stats


def ingest_in_batches(texts: list[str], metadatas: list[dict], ids: list[str], batch_size: int) -> None:
    """Write parsed documents to ChromaDB in batches."""
    total = len(texts)
    if total == 0:
        print("No records to ingest after filtering.")
        return

    print(f"Ingesting {total} records in batches of {batch_size}...")
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        add_documents(
            texts=texts[start:end],
            metadatas=metadatas[start:end],
            ids=ids[start:end],
        )
        batch_no = (start // batch_size) + 1
        batch_total = (total - 1) // batch_size + 1
        print(f"  Batch {batch_no}/{batch_total} complete ({end}/{total})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest MedMCQ explanations into ChromaDB")
    parser.add_argument("--json-path", type=Path, default=DEFAULT_JSON_PATH, help="Path to medmcq JSON file")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="Batch size for Chroma upsert")
    parser.add_argument("--min-explanation-len", type=int, default=120, help="Minimum explanation length to keep")
    parser.add_argument("--max-explanation-len", type=int, default=1200, help="Maximum explanation length to keep")
    parser.add_argument(
        "--skip-unknown-reference",
        action="store_true",
        help="Exclude rows where Reference is Unknown",
    )
    parser.add_argument(
        "--skip-mcq-style",
        action="store_true",
        help="Exclude rows containing MCQ-style answer patterns",
    )
    parser.add_argument(
        "--clear-existing",
        action="store_true",
        help="Delete existing Chroma collection before ingest",
    )
    parser.add_argument("--dry-run", action="store_true", help="Parse/filter only; do not write to Chroma")

    args = parser.parse_args()

    json_path = args.json_path
    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")

    print("MedMCQ Explanation Ingestion")
    print("=" * 40)
    print(f"JSON path: {json_path}")
    print(f"Collection size before: {collection_size()}")

    texts, metadatas, ids, stats = parse_records(
        json_path=json_path,
        min_explanation_len=args.min_explanation_len,
        max_explanation_len=args.max_explanation_len,
        skip_unknown_reference=args.skip_unknown_reference,
        skip_mcq_style=args.skip_mcq_style,
    )

    print("\nFilter summary:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    if args.dry_run:
        print("\nDry run complete. No data was written.")
        return

    if args.clear_existing and collection_size() > 0:
        print("\nDeleting existing Chroma collection...")
        delete_collection()
        print("Collection deleted.")

    ingest_in_batches(texts=texts, metadatas=metadatas, ids=ids, batch_size=args.batch_size)

    print("\nDone.")
    print(f"Collection size after: {collection_size()}")


if __name__ == "__main__":
    main()
