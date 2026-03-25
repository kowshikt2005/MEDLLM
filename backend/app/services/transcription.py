"""
Speech-to-text service using OpenAI's Whisper.

How it works:
  1. User records audio in the browser (WebM format)
  2. Browser sends the audio blob to POST /api/transcribe
  3. The transcribe router saves it to a temp file
  4. This service loads the Whisper model and transcribes the audio
  5. Returns the transcribed text + detected language

The model is loaded lazily on the first transcription request.
After that, it stays in memory for fast subsequent transcriptions.

Model sizes (trade-off: accuracy vs speed vs RAM):
  - "tiny"   ~39M params  — fastest, least accurate
  - "base"   ~74M params
  - "small"  ~244M params — good balance (default)
  - "medium" ~769M params
  - "large"  ~1550M params — most accurate, slowest
"""

import glob
import os

import whisper

from app.config import settings


def _ensure_ffmpeg_on_path():
    """
    On Windows, winget portable installs don't add executables to PATH.
    This function finds ffmpeg in known winget install locations and
    patches os.environ["PATH"] so Whisper's subprocess call can find it.

    This only runs once at module import time.
    """
    import shutil
    if shutil.which("ffmpeg"):
        return  # Already on PATH, nothing to do

    # Winget portable packages land here
    winget_packages = os.path.expandvars(
        r"%LOCALAPPDATA%\Microsoft\WinGet\Packages"
    )
    # The folder name includes a hash suffix, so we glob for it
    matches = glob.glob(os.path.join(winget_packages, "Gyan.FFmpeg*", "**", "bin"), recursive=True)
    if matches:
        ffmpeg_bin = matches[0]
        os.environ["PATH"] = ffmpeg_bin + os.pathsep + os.environ["PATH"]
        print(f"ffmpeg found and added to PATH: {ffmpeg_bin}")
    else:
        print("WARNING: ffmpeg not found. Transcription will fail. Install ffmpeg and add it to PATH.")


_ensure_ffmpeg_on_path()

# Global model reference — loaded once, reused for all requests
_model = None


def _get_model():
    """
    Load the Whisper model on first use (lazy loading).

    Why lazy? The model is ~1.5GB for "small". Loading it at import time
    would slow down server startup. Instead, we load it when someone
    actually needs transcription for the first time.
    """
    global _model
    if _model is None:
        print(f"Loading Whisper model: {settings.whisper_model}...")
        _model = whisper.load_model(settings.whisper_model)
        print(f"Whisper model loaded successfully")
    return _model


def transcribe(file_path: str) -> dict:
    """
    Transcribe an audio file to text.

    Args:
        file_path: Path to the audio file (WAV, MP3, WebM, etc.)

    Returns:
        dict with "text" (transcribed string) and "language" (detected language code)
    """
    model = _get_model()
    result = model.transcribe(file_path)

    return {
        "text": result["text"].strip(),
        "language": result.get("language"),
    }
