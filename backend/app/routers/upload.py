"""
File upload router — handles document and image uploads.

CHANGE: New pipeline with RAG-first architecture
Flow:
  1. User selects a file in the frontend
  2. Frontend sends it here (before the user types their message)
  3. We save the file to disk and extract text from it
  4. CHANGE: Chunk the text using file-type aware sizing
  5. CHANGE: Embed chunks and store in ChromaDB
  6. Create an Attachment row with metadata only (no extracted_text)
  7. Return the upload_id so frontend can reference it when sending chat
  8. When chat.py receives the message, it uses RAG to retrieve relevant chunks

Why upload before message?
  Text extraction (especially OCR and PDF parsing) takes time. By starting
  extraction when the user selects the file, the processing happens in the
  background while they type their question. By the time they hit send,
  the embeddings and RAG index are ready.
  
Why RAG-first instead of injecting full text?
  - Most of the file content is irrelevant to a specific question
  - Full text bloats the LLM prompt token count
  - RAG retrieves only semantically relevant chunks
  - Better performance and more focused responses
"""

import os
import uuid

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Attachment, get_db
from app.models.schemas import UploadResponse
from app.services.document_processor import detect_file_type, extract_text, chunk_text
from app.services import rag_service

router = APIRouter(prefix="/api", tags=["upload"])

# Where uploaded files are stored on disk
UPLOAD_DIR = os.path.join("data", "uploads")

# CHANGE: Batch size for adding chunks to ChromaDB
# Process embeddings in batches to manage memory usage
BATCH_SIZE = 50


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload and process a file (PDF, DOCX, image, or text).

    CHANGE: New RAG-first pipeline
    Steps:
      1. Determine file type from extension
      2. Save file to data/uploads/ with a unique name
      3. Extract text from the file
      4. CHANGE: Chunk text using file-type aware sizing
      5. CHANGE: Embed chunks and store in ChromaDB
      6. Create an Attachment record with metadata only
      7. Return the upload_id for the frontend to use later
    """
    # Ensure upload directory exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Detect what kind of file this is
    file_type = detect_file_type(file.filename)

    # Generate a unique filename to avoid collisions
    # Keep the original extension so Tesseract/pdfplumber can identify the format
    ext = os.path.splitext(file.filename)[1]
    unique_name = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)

    # Save the uploaded file to disk
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Extract text from the file
    extracted_text = await extract_text(file_path, file_type)

    # CHANGE: Chunk text using file-type aware sizing
    # Different file types benefit from different chunk configurations
    chunk_texts, chunk_metadatas, chunk_ids = chunk_text(
        extracted_text,
        source_name=file.filename,
        file_type=file_type,
    )

    # CHANGE: Embed and store chunks in ChromaDB
    # Only relevant chunks will be retrieved for RAG, not the entire file
    if chunk_texts:
        print(f"[Upload] Embedding {len(chunk_texts)} chunks from {file.filename}...")
        try:
            # Add chunks to ChromaDB in batches (memory efficiency)
            for i in range(0, len(chunk_texts), BATCH_SIZE):
                batch_texts = chunk_texts[i : i + BATCH_SIZE]
                batch_metas = chunk_metadatas[i : i + BATCH_SIZE]
                batch_ids = chunk_ids[i : i + BATCH_SIZE]
                rag_service.add_documents(batch_texts, batch_metas, batch_ids)
                print(f"[Upload] Batch {i // BATCH_SIZE + 1}/{(len(chunk_texts) - 1) // BATCH_SIZE + 1} stored in ChromaDB.")
        except Exception as e:
            print(f"[Upload] Error storing chunks in ChromaDB: {e}")

    # CHANGE: Create an Attachment record with metadata only
    # No extracted_text stored — it's in ChromaDB, retrievable via RAG
    attachment = Attachment(
        filename=file.filename,
        file_type=file_type,
        file_path=file_path,
        # CHANGE: extracted_text field removed
    )
    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)

    print(f"[Upload] File {file.filename} processed: {len(chunk_texts)} chunks created")

    return UploadResponse(
        upload_id=attachment.id,
        filename=file.filename,
        file_type=file_type,
        # CHANGE: extracted_text not returned — client doesn't need it
    )
