"""
Pydantic schemas for API request/response validation.

These define the SHAPE of data flowing in and out of the API.
FastAPI uses these to:
  1. Validate incoming requests (reject bad data automatically)
  2. Serialize outgoing responses (convert Python objects to JSON)
  3. Generate API documentation (the /docs page)
"""

from datetime import datetime

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════════════

class SignupRequest(BaseModel):
    """What the frontend sends when a user registers."""
    email: str = Field(..., min_length=3, description="User's email address")
    password: str = Field(..., min_length=6, description="Password (min 6 chars)")
    full_name: str = Field(..., min_length=1, description="User's full name")
    phone_number: str | None = None


class LoginRequest(BaseModel):
    """What the frontend sends when a user logs in."""
    email: str
    password: str


class TokenResponse(BaseModel):
    """What the backend returns after successful login/signup."""
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    """Public user info (never includes password hash)."""
    id: str
    email: str
    full_name: str


# ═══════════════════════════════════════════════════════════
# CHAT
# ═══════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    """What the frontend sends for each chat message."""
    message: str = Field(..., min_length=1, description="The user's message text")
    conversation_id: str | None = None  # None = start a new conversation
    attachments: list[str] = []  # List of upload IDs (for multimodal — Phase 2)
    health_context: bool = False  # Whether to include user's health profile in prompt
    mode: str = "normal"  # "normal" or "reasoning" (Phase 4)


class MessageResponse(BaseModel):
    """A single message in a conversation."""
    id: str
    role: str  # "user" or "assistant"
    content: str
    created_at: datetime


class ConversationResponse(BaseModel):
    """Summary of a conversation (for the sidebar list)."""
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class ConversationDetailResponse(BaseModel):
    """Full conversation with all messages."""
    id: str
    title: str
    messages: list[MessageResponse]
    created_at: datetime


# ═══════════════════════════════════════════════════════════
# HEALTH PROFILE
# ═══════════════════════════════════════════════════════════

class HealthProfileRequest(BaseModel):
    """What the frontend sends from the UserProfile form."""
    age: int | None = None
    gender: str | None = None
    height: float | None = None
    weight: float | None = None
    blood_type: str | None = None
    allergies: str | None = None
    medications: str | None = None
    conditions: str | None = None
    exercise_frequency: str | None = None
    smoking_status: str | None = None
    alcohol_consumption: str | None = None


class HealthProfileResponse(HealthProfileRequest):
    """What the backend returns — same fields plus metadata."""
    id: str
    updated_at: datetime | None = None


# ═══════════════════════════════════════════════════════════
# FILE UPLOAD (Phase 2 — placeholder for now)
# ═══════════════════════════════════════════════════════════

class UploadResponse(BaseModel):
    """What the backend returns after processing an uploaded file."""
    upload_id: str
    filename: str
    file_type: str
    extracted_text: str
    preview_url: str | None = None
