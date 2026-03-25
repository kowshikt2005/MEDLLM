"""
FastAPI application entry point.

This file:
  1. Creates the FastAPI app instance
  2. Configures CORS (so the React frontend can talk to the backend)
  3. Registers all routers (URL endpoint groups)
  4. Sets up the database on startup

Run with: uvicorn app.main:app --reload
The --reload flag auto-restarts the server when you change code (dev only).
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models.database import init_db
from app.routers import auth, chat, upload, transcribe


# ── Lifespan event ──────────────────────────────────────
# This runs ONCE when the server starts up, before any requests are handled.
# We use it to create database tables if they don't exist yet.
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup/shutdown lifecycle.

    The code BEFORE 'yield' runs on startup.
    The code AFTER 'yield' runs on shutdown.
    """
    print(f"🏥 Starting {settings.app_name}...")
    print(f"📊 Database: {settings.database_url}")
    print(f"🤖 Ollama: {settings.ollama_host} (model: {settings.ollama_model})")

    # Create all database tables
    await init_db()
    print("✅ Database initialized")

    yield  # Server is now running and accepting requests

    print(f"👋 Shutting down {settings.app_name}...")


# ── Create the app ──────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    description="Multimodal Medical AI Assistant with RAG and Agentic Reasoning",
    version="1.0.0",
    lifespan=lifespan,
)


# ── CORS middleware ─────────────────────────────────────
# CORS = Cross-Origin Resource Sharing
#
# Your React frontend runs on http://localhost:5173
# Your FastAPI backend runs on http://localhost:8000
#
# By default, browsers BLOCK requests between different origins (ports count).
# CORS middleware tells the browser "it's OK, I trust requests from this origin."
#
# Without this, every API call from React would fail with:
#   "Access to fetch at 'http://localhost:8000' from origin
#    'http://localhost:5173' has been blocked by CORS policy"
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:4173",   # Vite preview
        "http://localhost:3000",   # Alternative dev port
    ],
    allow_credentials=True,        # Allow cookies/auth headers
    allow_methods=["*"],           # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],           # Allow all headers (including Authorization)
)


# ── Register routers ────────────────────────────────────
# Each router handles a group of related endpoints.
# The prefix in each router determines the URL path.
app.include_router(auth.router)         # /api/auth/signup, /api/auth/login
app.include_router(chat.router)         # /api/chat
app.include_router(upload.router)       # /api/upload
app.include_router(transcribe.router)   # /api/transcribe


# ── Health check endpoint ───────────────────────────────
@app.get("/api/health")
async def health_check():
    """
    Simple endpoint to verify the server is running.
    Also checks if Ollama is reachable.
    """
    from app.services.llm_service import llm_service

    return {
        "status": "healthy",
        "ollama_available": llm_service.is_available(),
        "model": settings.ollama_model,
    }
