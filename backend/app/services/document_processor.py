"""
Document processing service — extracts text from uploaded files.

Supports:
  - PDF: uses pdfplumber to extract text from each page
  - DOCX: uses python-docx to extract paragraph text
  - Images (PNG, JPG, etc.): uses Tesseract OCR to read text in images
  - Text files (.txt, .csv, .md): reads raw content directly

How it fits in the pipeline:
  1. User uploads a file via POST /api/upload
  2. The upload router saves the file to disk
  3. This service extracts text from the saved file
  4. The extracted text is chunked into smaller pieces (CHANGE: file-type aware)
  5. Chunks are embedded and stored in ChromaDB for RAG
  6. Only metadata is stored in SQLite (CHANGE: no full text stored)
  7. When the user sends a chat message, RAG retrieves relevant chunks for context
"""

import hashlib
import os

import pdfplumber
import pytesseract
from docx import Document
from PIL import Image


# CHANGE: File-type aware chunk configuration
# Different document types have different optimal chunk sizes:
# - PDFs benefit from larger chunks due to structured content
# - DOCX documents are narrative and can use medium chunks
# - Text/CSV/Markdown are often dense and use smaller chunks
# - OCR text is less reliable so smaller chunks work better
CHUNK_CONFIG = {
    "pdf": {"chunk_size": 1200, "overlap": 200},
    "docx": {"chunk_size": 1000, "overlap": 150},
    "text": {"chunk_size": 800, "overlap": 120},
    "image": {"chunk_size": 700, "overlap": 100},
}


async def extract_text(file_path: str, file_type: str) -> str:
    """
    Extract readable text from a file based on its type.

    Args:
        file_path: Path to the saved file on disk
        file_type: One of "pdf", "docx", "image", "text"

    Returns:
        Extracted text as a string. Empty string if extraction fails.
    """
    try:
        if file_type == "pdf":
            return _extract_pdf(file_path)
        elif file_type == "docx":
            return _extract_docx(file_path)
        elif file_type == "image":
            return _extract_image_ocr(file_path)
        elif file_type == "text":
            return _extract_text_file(file_path)
        else:
            return ""
    except Exception as e:
        print(f"Error extracting text from {file_path}: {e}")
        return f"[Error extracting text: {e}]"


def _extract_pdf(file_path: str) -> str:
    """
    Extract text from a PDF using pdfplumber.

    pdfplumber reads each page and pulls out text while preserving layout.
    It's better than PyPDF2 for tables and complex layouts.
    """
    text_parts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)


def _extract_docx(file_path: str) -> str:
    """
    Extract text from a Word document using python-docx.

    Reads all paragraphs in order. Skips empty paragraphs.
    """
    doc = Document(file_path)
    text_parts = []
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            text_parts.append(paragraph.text)
    return "\n\n".join(text_parts)


def _extract_image_ocr(file_path: str) -> str:
    """
    Extract text from an image using Tesseract OCR.

    Tesseract is an open-source OCR engine. It reads text visible in images
    (like scanned documents, photos of whiteboards, medical labels, etc.).

    The user must install Tesseract separately:
      Windows: download from https://github.com/UB-Mannheim/tesseract/wiki
    """
    image = Image.open(file_path)
    text = pytesseract.image_to_string(image)
    return text.strip()


def _extract_text_file(file_path: str) -> str:
    """Read a plain text file directly."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def detect_file_type(filename: str) -> str:
    """
    Determine the file type from the filename extension.

    Returns one of: "pdf", "docx", "image", "text", "unknown"
    """
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".pdf":
        return "pdf"
    elif ext in (".docx", ".doc"):
        return "docx"
    elif ext in (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"):
        return "image"
    elif ext in (".txt", ".csv", ".md", ".json", ".xml"):
        return "text"
    else:
        return "unknown"


# CHANGE: New function to chunk text with file-type aware sizing
def chunk_text(
    text: str,
    source_name: str,
    file_type: str = "text",
) -> tuple[list[str], list[dict], list[str]]:
    """
    Split a long text into overlapping chunks with file-type aware sizing.

    CHANGE: Uses different chunk sizes and overlaps based on file_type:
      - PDF: 1200 chars, 200 overlap (structured, can be verbose)
      - DOCX: 1000 chars, 150 overlap (narrative, medium density)
      - Text/CSV/MD: 800 chars, 120 overlap (often dense)
      - Image (OCR): 700 chars, 100 overlap (less reliable, use smaller chunks)

    Returns three parallel lists (same length, same indices):
      texts:     the actual chunk content
      metadatas: {"source": filename, "chunk_index": i, "file_type": type} for each chunk
      ids:       unique stable ID for each chunk

    Args:
        text:        the full extracted text from a document
        source_name: the filename, used in metadata and IDs
        file_type:   one of "pdf", "docx", "text", "image" (default "text")

    Returns:
        (texts, metadatas, ids) - three parallel lists
    """
    # Get chunk config for this file type (default to "text" if not found)
    config = CHUNK_CONFIG.get(file_type, CHUNK_CONFIG["text"])
    chunk_size = config["chunk_size"]
    chunk_overlap = config["overlap"]

    texts = []
    metadatas = []
    ids = []

    chunk_index = 0
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()

        if chunk:  # Skip empty chunks (can happen at end of text)
            # Stable ID: filename + chunk index + first 8 chars of content hash
            # This means the same content always gets the same ID
            content_hash = hashlib.md5(chunk.encode()).hexdigest()[:8]
            chunk_id = f"{source_name}_chunk_{chunk_index}_{content_hash}"

            texts.append(chunk)
            metadatas.append({
                "source": source_name,
                "chunk_index": chunk_index,
                "file_type": file_type,  # CHANGE: Track original file type
            })
            ids.append(chunk_id)
            chunk_index += 1

        # Advance by (chunk_size - overlap) so consecutive chunks overlap
        start += chunk_size - chunk_overlap

    return texts, metadatas, ids
