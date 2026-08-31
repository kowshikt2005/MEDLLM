"""Build a reproducible, curated local source corpus for MedLLM.

Default use (after snapshots have been refreshed):
    python scripts/build_curated_index.py --verify-only
    python scripts/build_curated_index.py --replace-curated

Refreshing contacts the official URLs in manifest.json. It is deliberate because
health pages may change; refresh creates local text snapshots and records their
SHA-256 digests before any indexing is attempted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen


BACKEND_DIR = Path(__file__).resolve().parents[1]
CURATED_SOURCES_DIR = BACKEND_DIR / "data" / "curated_sources"
MANIFEST_PATH = CURATED_SOURCES_DIR / "manifest.json"
BLOCK_TAGS = {"article", "div", "h1", "h2", "h3", "h4", "li", "p", "section"}
IGNORED_TAGS = {"aside", "footer", "form", "nav", "script", "style", "svg"}


class MainTextExtractor(HTMLParser):
    """Extract readable text from a page's main element without page chrome."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._main_depth = 0
        self._ignored_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "main":
            self._main_depth += 1
            return
        if not self._main_depth:
            return
        if tag in IGNORED_TAGS:
            self._ignored_depth += 1
            return
        if not self._ignored_depth and tag in BLOCK_TAGS:
            self._parts.append("\n\n")

    def handle_endtag(self, tag: str) -> None:
        if tag == "main" and self._main_depth:
            self._main_depth -= 1
            return
        if not self._main_depth:
            return
        if tag in IGNORED_TAGS and self._ignored_depth:
            self._ignored_depth -= 1
            return
        if not self._ignored_depth and tag in BLOCK_TAGS:
            self._parts.append("\n\n")

    def handle_data(self, data: str) -> None:
        if self._main_depth and not self._ignored_depth:
            normalized = re.sub(r"\s+", " ", data)
            if normalized.strip():
                self._parts.append(normalized.strip())

    def text(self) -> str:
        text = "".join(self._parts)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n[ \t]+", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def extract_main_text(html: str) -> str:
    """Return normalized visible text from the page main element."""
    parser = MainTextExtractor()
    parser.feed(html)
    parser.close()
    text = parser.text()
    if not text:
        raise ValueError("No text was found inside the page main element.")
    return text


def load_manifest(manifest_path: Path = MANIFEST_PATH) -> list[dict]:
    """Load the supported source entries and validate their essential provenance."""
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    sources = payload.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("The curated source manifest must contain a non-empty sources list.")

    required = {"source_id", "title", "url", "snapshot", "publisher"}
    for source in sources:
        missing = required - source.keys()
        if missing:
            raise ValueError(f"Source {source!r} is missing required fields: {sorted(missing)}")
        if not source["url"].startswith("https://www.cdc.gov/"):
            raise ValueError(f"Only approved CDC URLs are allowed: {source['url']}")
    return sources


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_source_request(url: str) -> Request:
    """Build a standards-compatible request for the approved public CDC pages."""
    return Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/137.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )


def refresh_sources(sources: list[dict], source_dir: Path) -> None:
    """Download each official page and store only its readable main text."""
    source_dir.mkdir(parents=True, exist_ok=True)
    for source in sources:
        request = build_source_request(source["url"])
        with urlopen(request, timeout=30) as response:  # nosec B310 -- URLs are manifest-validated HTTPS CDC URLs
            html = response.read().decode("utf-8", errors="replace")
        snapshot = source_dir / source["snapshot"]
        snapshot.write_text(extract_main_text(html) + "\n", encoding="utf-8")
        source["snapshot_sha256"] = sha256_file(snapshot)
        print(f"Refreshed {source['source_id']}: {source['snapshot_sha256']}")


def verify_snapshots(sources: list[dict], source_dir: Path) -> list[tuple[dict, Path]]:
    """Fail closed when a required source snapshot is absent or differs from the manifest."""
    verified: list[tuple[dict, Path]] = []
    for source in sources:
        snapshot = source_dir / source["snapshot"]
        expected = source.get("snapshot_sha256")
        if not snapshot.is_file():
            raise ValueError(f"Missing curated snapshot: {snapshot}")
        if not expected:
            raise ValueError(f"Source {source['source_id']} has no pinned snapshot SHA-256.")
        actual = sha256_file(snapshot)
        if actual != expected:
            raise ValueError(
                f"Snapshot digest mismatch for {source['source_id']}: expected {expected}, got {actual}."
            )
        verified.append((source, snapshot))
    return verified


def build_curated_index(verified_sources: list[tuple[dict, Path]], batch_size: int) -> int:
    """Replace only curated chunks, preserving user-uploaded chunks in the collection."""
    sys.path.insert(0, str(BACKEND_DIR))
    from app.services.document_processor import chunk_text
    from app.services.rag_service import add_documents, delete_documents_by_corpus

    delete_documents_by_corpus("curated")
    indexed_chunks = 0
    for source, snapshot in verified_sources:
        text = snapshot.read_text(encoding="utf-8")
        texts, metadatas, ids = chunk_text(text, source["source_id"], file_type="text")
        for metadata in metadatas:
            metadata.update(
                {
                    "corpus": "curated",
                    "source_id": source["source_id"],
                    "reference": source["title"],
                    "url": source["url"],
                    "publisher": source["publisher"],
                    "snapshot_sha256": source["snapshot_sha256"],
                }
            )
        for start in range(0, len(texts), batch_size):
            add_documents(
                texts[start : start + batch_size],
                metadatas[start : start + batch_size],
                ids[start : start + batch_size],
            )
        indexed_chunks += len(texts)
        print(f"Indexed {source['source_id']}: {len(texts)} chunks")
    return indexed_chunks


def write_manifest(manifest_path: Path, sources: list[dict]) -> None:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["sources"] = sources
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-sources", action="store_true", help="Download approved CDC pages into pinned local snapshots.")
    parser.add_argument("--update-hashes", action="store_true", help="Write refreshed snapshot SHA-256 values to the manifest.")
    parser.add_argument("--verify-only", action="store_true", help="Validate local snapshots and digests without indexing.")
    parser.add_argument("--replace-curated", action="store_true", help="Replace curated chunks only; user-uploaded chunks remain untouched.")
    parser.add_argument("--batch-size", type=int, default=50, help="Number of chunks embedded per batch (default: 50).")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.update_hashes and not args.refresh_sources:
        raise SystemExit("--update-hashes requires --refresh-sources.")
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be at least 1.")

    sources = load_manifest()
    if args.refresh_sources:
        refresh_sources(sources, CURATED_SOURCES_DIR)
        if args.update_hashes:
            write_manifest(MANIFEST_PATH, sources)

    if args.verify_only or args.replace_curated:
        verified = verify_snapshots(sources, CURATED_SOURCES_DIR)
        print(f"Verified {len(verified)} curated source snapshots.")
        if args.replace_curated:
            indexed = build_curated_index(verified, args.batch_size)
            print(f"Indexed {indexed} curated chunks.")
    elif not args.refresh_sources:
        raise SystemExit("Choose --verify-only, --replace-curated, or --refresh-sources.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
