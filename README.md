# MedLLM — Multimodal Medical AI Assistant

A project for my practical knowledge and experience on LLM applications.

MedLLM is a full-stack medical AI assistant that combines local LLM inference, a RAG pipeline, and multimodal input processing. The current default runtime model is `medllama:latest` via Ollama.

## What It Does

- **Medical Q&A** - Ask health-related questions and get streaming responses from a locally running LLM
- **Multimodal Input** - Upload PDFs, images, documents, or use voice; content is converted to text and fed into retrieval + generation
- **RAG Pipeline** - Retrieves relevant medical knowledge from ChromaDB and returns source-backed answers
- **Reasoning Mode** - Breaks complex questions into sub-queries, retrieves evidence for each, and synthesizes a clinician-style answer
- **Source Citations** - Returns deduplicated sources with bounded confidence scores in the chat UI

## Architecture

```
React Frontend (Vite + Tailwind)
       |
       v
FastAPI Backend (Python)
       |
  +----+--------------+
  |    |              |
  v    v              v
Ollama   ChromaDB    Whisper
(LLM)    (RAG)       (Voice STT)
  |
  +-- medllama:latest (current default model)
```

**Multimodal Processing:**
```
Voice  --> faster-whisper --> text --+
Image  --> pytesseract OCR --> text -+
PDF    --> pdfplumber ------> text --+--> RAG retrieval --> LLM --> streaming response
DOCX   --> python-docx -----> text -+
Text   ---------------------------------+
```

## Tech Stack

| Layer | Tech |
|---|---|
| Frontend | React, Vite, Tailwind CSS |
| Backend | FastAPI, SQLAlchemy, SQLite |
| LLM Inference | Ollama (local), medllama:latest (default) |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Streaming | Server-Sent Events (SSE) |
| RAG | ChromaDB + sentence-transformers + CrossEncoder reranking |
| Voice | faster-whisper (STT) |
| Document Processing | pdfplumber, pytesseract, python-docx |
| Optional Cloud Model | Groq (used by reasoning mode when configured) |

## Project Structure

```
MEDLLM/
├── frontend/              # React + Vite + Tailwind
│   ├── src/
│   │   ├── components/    # UI components (Chat, Auth, Dashboard, etc.)
│   │   └── services/      # API client with SSE streaming
│   └── package.json
├── backend/               # FastAPI
│   ├── app/
│   │   ├── main.py        # App entry point, CORS, health check
│   │   ├── config.py      # Environment config via pydantic-settings
│   │   ├── models/        # SQLAlchemy models + Pydantic schemas
│   │   ├── routers/       # API endpoints (auth, chat)
│   │   ├── services/      # LLM client, RAG, document processing
│   │   └── prompts/       # System prompts and templates
│   └── requirements.txt
├── PLAN.md                # Implementation roadmap
└── CHANGELOG.md           # Detailed development log
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- [Ollama](https://ollama.com/) installed and running

### Setup

**1. Pull the current local model:**
```bash
ollama pull medllama:latest
```

**2. Start the backend:**
```bash
cd backend
python -m venv venv
# Windows PowerShell
.\venv\Scripts\Activate.ps1
# Windows CMD
# venv\Scripts\activate.bat
# Mac/Linux
# source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

**3. Start the frontend:**
```bash
cd frontend
npm install
npm run dev
```

**4. Open the app:**
Visit `http://localhost:5173`

## Current Runtime Settings

These are the active defaults in this workspace:

- `OLLAMA_HOST=http://localhost:11434`
- `OLLAMA_MODEL=medllama:latest`
- `WHISPER_MODEL=small`
- `DEBUG=true`
- Groq is optional and used for reasoning-mode remote inference when enabled.

Behavior notes:

- Normal chat mode emits step/progress events over SSE.
- Assistant output is clinician-facing and formatted for readability.
- Citations are deduplicated and shown with clamped confidence percentages.

## Benchmarks

Model accuracy on [MedQA USMLE](https://huggingface.co/datasets/GBaker/MedQA-USMLE-4-options), evaluated with `backend/scripts/benchmark_medqa.py` at `temperature=0`.

Run commands:

```bash
cd backend
.\venv\Scripts\python.exe scripts\benchmark_medqa.py --provider ollama --model medllama:latest --n 100
.\venv\Scripts\python.exe scripts\benchmark_medqa.py --compare
```

| Model | Where it runs | MedQA Accuracy | Notes |
|---|---|---|---|
| Random guessing | — | 25.0% | 4-option baseline |
| **medllama:latest** | Local via Ollama | **4.0%** | Current default model · 2026-04-18 (100Q, 83 unparseable) |
| **Mistral-7B** (base) | Local via Ollama | **47.0%** | Pre fine-tune · 2026-03-29 |
| Human passing threshold | — | ~60.0% | USMLE Step 1 pass mark |
| **LLaMA-3.3-70B** | Groq cloud API | **75.0%** | 10× larger model · 2026-03-29 |

## Implementation Phases

- [x] **Phase 1** — Backend foundation + text chat with streaming
- [x] **Phase 2** — Multimodal input (PDF, image OCR, voice transcription)
- [x] **Phase 3** — RAG pipeline with ChromaDB
- [x] **Phase 4** — Reasoning / agent mode via free API (Groq/Gemini)
- [ ] **Phase 5** — Optional QLoRA fine-tuning on medical data
- [ ] **Phase 6** — Profile, history, polish, Docker deployment
