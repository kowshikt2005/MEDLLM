"""
File upload router — handles document and image uploads.

Flow:
  1. User selects a file in the frontend
  2. Frontend immediately sends it here (before the user types their message)
  3. We save the file to disk, extract text from it, create an Attachment row
  4. Return the upload_id so the frontend can reference it when sending the chat message
  5. When chat.py receives the message with attachment IDs, it looks up the extracted text

Why upload on selection (not on send)?
  Text extraction (especially OCR and PDF parsing) takes time. By starting
  extraction when the user selects the file, the processing happens in the
  background while they type their question. By the time they hit send,
  the text is already extracted and ready.
"""

import os
import uuid

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Attachment, get_db
from app.models.schemas import UploadResponse
from app.services.document_processor import detect_file_type, extract_text

router = APIRouter(prefix="/api", tags=["upload"])

# Where uploaded files are stored on disk
UPLOAD_DIR = os.path.join("data", "uploads")


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload and process a file (PDF, DOCX, image, or text).

    Steps:
      1. Determine file type from extension
      2. Save file to data/uploads/ with a unique name
      3. Extract text from the file
      4. Create an Attachment record (message_id is null for now)
      5. Return the upload_id for the frontend to use later
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

    # Create an Attachment record in the database
    # message_id is null because the user hasn't sent their message yet
    attachment = Attachment(
        filename=file.filename,
        file_type=file_type,
        file_path=file_path,
        extracted_text=extracted_text,
    )
    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)

    return UploadResponse(
        upload_id=attachment.id,
        filename=file.filename,
        file_type=file_type,
        extracted_text=extracted_text,
    )
