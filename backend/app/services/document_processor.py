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
  4. The extracted text is stored in the Attachment row
  5. When the user sends a chat message, chat.py injects this text into the LLM prompt
"""

import os

import pdfplumber
import pytesseract
from docx import Document
from PIL import Image


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
