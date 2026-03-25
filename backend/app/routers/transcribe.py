"""
Audio transcription router — converts speech to text using Whisper.

Flow:
  1. User clicks the mic button in the frontend and records audio
  2. When they stop recording, the browser captures a WebM audio blob
  3. Frontend sends that blob here as a file upload
  4. We save it to a temp file, run Whisper on it, return the text
  5. Frontend puts the transcribed text into the chat input box
  6. User can edit the text before sending

Why not stream the transcription?
  Whisper processes the entire audio file at once (not in real-time).
  For short voice messages (< 1 minute), this takes just a few seconds
  on a modern CPU. Real-time streaming would require a different model.
"""

import os
import tempfile

from fastapi import APIRouter, UploadFile, File

from app.models.schemas import TranscriptionResponse
from app.services.transcription import transcribe

router = APIRouter(prefix="/api", tags=["transcribe"])


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Transcribe an audio file to text.

    Accepts audio in any format Whisper supports (WebM, WAV, MP3, etc.).
    Returns the transcribed text and detected language.
    """
    # Save the uploaded audio to a temp file
    # Whisper needs a file path, not a stream
    suffix = os.path.splitext(file.filename or ".webm")[1]
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)

    try:
        content = await file.read()
        tmp.write(content)
        tmp.close()

        # Run Whisper transcription
        result = transcribe(tmp.name)

        return TranscriptionResponse(
            text=result["text"],
            language=result.get("language"),
        )
    finally:
        # Clean up the temp file
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)
