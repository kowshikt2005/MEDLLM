# MedLLM — Multimodal Medical AI Assistant

A project for my practical knowledge and experience on LLM applications.

MedLLM is a full-stack medical AI assistant that combines a fine-tuned LLM, RAG pipeline, and multimodal input processing — all running locally via Ollama with no paid API dependencies.

## What It Does

- **Medical Q&A** — Ask health-related questions and get streaming responses from a locally-running LLM
- **Multimodal Input** — Upload PDFs, images, documents, or use voice — all converted to text and fed to the LLM
- **RAG Pipeline** — Retrieves relevant medical knowledge from a vector database to ground responses in sources
- **Reasoning Mode** — An agentic mode that breaks complex questions into sub-queries, retrieves evidence for each, and synthesizes a comprehensive answer with citations
- **Fine-Tuned Model** — Custom QLoRA fine-tuned Mistral-7B on medical data, served locally via Ollama

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
Ollama  ChromaDB    Whisper
(LLM)  (RAG)       (Voice STT)
  |
  +-- Fine-tuned Mistral-7B (QLoRA)
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
| LLM Inference | Ollama (local), Mistral-7B |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Streaming | Server-Sent Events (SSE) |
| RAG | ChromaDB + sentence-transformers |
| Voice | faster-whisper (STT) |
| Document Processing | pdfplumber, pytesseract, python-docx |
| Fine-Tuning | QLoRA via Hugging Face + PEFT (Google Colab) |

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

**1. Pull an LLM model:**
```bash
ollama pull mistral
```

**2. Start the backend:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**3. Start the frontend:**
```bash
cd frontend
npm install
npm run dev
```

**4. Open the app:**
Visit `http://localhost:5173`

## Benchmarks

Model accuracy on [MedQA USMLE](https://huggingface.co/datasets/GBaker/MedQA-USMLE-4-options) — 100-question random sample from the test split, temperature=0.

| Model | Where it runs | MedQA Accuracy | Notes |
|---|---|---|---|
| Random guessing | — | 25.0% | 4-option baseline |
| **Mistral-7B** (base) | Local via Ollama | **47.0%** | Pre fine-tune · 2026-03-29 |
| **Mistral-7B (fine-tuned)** | Local via Ollama | _pending_ | After QLoRA on MedAlpaca |
| Human passing threshold | — | ~60.0% | USMLE Step 1 pass mark |
| **LLaMA-3.3-70B** | Groq cloud API | **75.0%** | 10× larger model · 2026-03-29 |

> **Fine-tuning goal:** lift Mistral-7B from 47% toward the human passing threshold (~60%) using QLoRA on medical Q&A data — while keeping inference fully local and free.

## Implementation Phases

- [x] **Phase 1** — Backend foundation + text chat with streaming
- [x] **Phase 2** — Multimodal input (PDF, image OCR, voice transcription)
- [x] **Phase 3** — RAG pipeline with ChromaDB
- [x] **Phase 4** — Reasoning / agent mode via free API (Groq/Gemini)
- [ ] **Phase 5** — QLoRA fine-tuning on medical data
- [ ] **Phase 6** — Profile, history, polish, Docker deployment
