"""
Database models and engine setup.

This file defines:
1. The async database engine (how Python talks to SQLite)
2. The session factory (how we create database "conversations")
3. All the database tables as Python classes (the ORM models)

Each class below maps to a TABLE in the SQLite database.
Each attribute maps to a COLUMN in that table.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

from app.config import settings


# ── Engine + Session ─────────────────────────────────────
# The "engine" is the connection to the database file.
# "async" means it won't block the server while waiting for disk I/O.
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,  # When True, prints SQL queries to console (helpful for learning!)
)

# A "session" is like a conversation with the database.
# You open one, do reads/writes, then close it.
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# Base class that all our table models inherit from
class Base(DeclarativeBase):
    pass


# ── Helper ───────────────────────────────────────────────
def generate_uuid() -> str:
    """Generate a unique ID for each row. UUIDs are random and globally unique."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Current time in UTC. Always use UTC in databases to avoid timezone bugs."""
    return datetime.now(timezone.utc)


# ── Table: users ─────────────────────────────────────────
class User(Base):
    """
    Stores registered users.
    One user can have one health profile and many conversations.
    """

    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    # Relationships: SQLAlchemy automatically joins these when accessed
    health_profile = relationship("HealthProfile", back_populates="user", uselist=False)
    conversations = relationship("Conversation", back_populates="user")


# ── Table: health_profiles ───────────────────────────────
class HealthProfile(Base):
    """
    Stores the user's medical profile.
    These fields match EXACTLY what the UserProfile.jsx form collects.
    This data gets injected into LLM prompts for personalized responses.
    """

    __tablename__ = "health_profiles"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    height = Column(Float, nullable=True)  # in cm
    weight = Column(Float, nullable=True)  # in kg
    blood_type = Column(String, nullable=True)
    allergies = Column(Text, nullable=True)
    medications = Column(Text, nullable=True)
    conditions = Column(Text, nullable=True)
    exercise_frequency = Column(String, nullable=True)
    smoking_status = Column(String, nullable=True)
    alcohol_consumption = Column(String, nullable=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    user = relationship("User", back_populates="health_profile")


# ── Table: conversations ─────────────────────────────────
class Conversation(Base):
    """
    A chat conversation. Each conversation has many messages.
    The 'title' is auto-generated from the first user message.
    """

    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, default="New Conversation")
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at")


# ── Table: messages ──────────────────────────────────────
class Message(Base):
    """
    A single message in a conversation.
    'role' is either "user" or "assistant".
    """

    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=generate_uuid)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    conversation = relationship("Conversation", back_populates="messages")
    attachments = relationship("Attachment", back_populates="message")


# ── Table: attachments ───────────────────────────────────
class Attachment(Base):
    """
    Files attached to a message (images, PDFs, documents).
    'extracted_text' stores what we pulled out of the file for the LLM.
    """

    __tablename__ = "attachments"

    id = Column(String, primary_key=True, default=generate_uuid)
    message_id = Column(String, ForeignKey("messages.id"), nullable=True)  # Null until message is sent
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # "pdf", "image", "docx", etc.
    file_path = Column(String, nullable=False)  # Where it's stored on disk
    extracted_text = Column(Text, nullable=True)  # Text extracted from the file
    created_at = Column(DateTime, default=utc_now)

    message = relationship("Message", back_populates="attachments")


# ── Table: feedback ──────────────────────────────────────
class Feedback(Base):
    """
    Thumbs up/down on assistant messages.
    Useful for evaluating model quality later.
    """

    __tablename__ = "feedback"

    id = Column(String, primary_key=True, default=generate_uuid)
    message_id = Column(String, ForeignKey("messages.id"), nullable=False)
    feedback_type = Column(String, nullable=False)  # "positive" or "negative"
    created_at = Column(DateTime, default=utc_now)


# ── Database initialization ──────────────────────────────
async def init_db():
    """
    Create all tables if they don't exist yet.
    Called once when the FastAPI app starts up.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ── Dependency for FastAPI routes ────────────────────────
async def get_db():
    """
    Creates a database session for each API request.
    FastAPI's dependency injection calls this automatically.

    The 'yield' makes it a generator:
    1. Open session → hand it to the route handler
    2. Route does its work
    3. Session is closed (even if an error occurred)
    """
    async with AsyncSessionLocal() as session:
        yield session
