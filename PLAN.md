# MedLLM — Full-Stack Multimodal Medical AI Assistant

## Context

The MedLLM project is currently a **frontend-only** React app with a polished UI (auth, chat, profile, landing page) but zero backend. All LLM responses are hardcoded `setTimeout` mocks. The goal is to turn this into a **resume-worthy full-stack project** with:
- A fine-tuned medical LLM (QLoRA on free Colab GPU)
- RAG pipeline with medical knowledge base
- Multimodal input (text, voice, image, PDF, documents)
- Local inference via Ollama (no paid APIs required)

---

## Architecture

```
React Frontend (Vite + Tailwind)
       │
       ▼
FastAPI Backend (Python)
       │
  ┌────┼──────────────┐
  │    │              │
  ▼    ▼              ▼
Ollama  ChromaDB    Whisper
(LLM)  (RAG)       (Voice STT)
  │
  └─ Fine-tuned Mistral-7B (QLoRA)
```

**Multimodal Processing Flow:**
```
Voice  ──► faster-whisper ──► text ──┐
Image  ──► pytesseract OCR ──► text ──┤
PDF    ──► pdfplumber ──────► text ──┼──► RAG retrieval ──► LLM prompt ──► streaming response
DOCX   ──► python-docx ────► text ──┤
Text   ──────────────────────────────┘
```

**Dual Chat Modes:**
```
NORMAL MODE (fast, ~15s):
  User query ──► RAG ──► Local Mistral-7B ──► streaming response

REASONING / AGENT MODE (thorough, ~30-45s):
  User query
      │
      ▼
  Free API (Groq/Gemini 70B) ── "The Reasoner"
      │
      ├─► Step 1: Analyze query, break into sub-questions
      ├─► Step 2: For each sub-question: RAG retrieval + local model
      ├─► Step 3: Synthesize all sub-answers
      ├─► Step 4: Review for accuracy, flag uncertainties
      └─► Final comprehensive response with sources + confidence
```

---

## Implementation Phases

### Phase 1: Backend Foundation + Text Chat ✅ IN PROGRESS
**Milestone: Type a message → get streaming response from Ollama**

- [x] Create PLAN.md
- [ ] Create `backend/` directory with FastAPI app structure
- [ ] `app/main.py` — FastAPI with CORS, lifespan events
- [ ] `app/config.py` — Settings via pydantic-settings
- [ ] `app/models/database.py` — SQLAlchemy models with SQLite
- [ ] `app/models/schemas.py` — Pydantic request/response schemas
- [ ] `app/services/llm_service.py` — Ollama client wrapper with streaming
- [ ] `app/routers/chat.py` — SSE streaming chat endpoint
- [ ] `app/routers/auth.py` — JWT auth (bcrypt + python-jose)
- [ ] Move existing frontend into `frontend/` subdirectory
- [ ] Create `frontend/src/services/api.js` — centralized API client
- [ ] Modify `ChatView.jsx` — replace setTimeout with real streaming API
- [ ] Modify `AuthView.jsx` — wire to real auth endpoints
- [ ] Add `/api` proxy in `vite.config.ts`

### Phase 2: Multimodal Input Pipeline
**Milestone: Upload PDF/image/voice → LLM responds about the content**

- [ ] `app/services/document_processor.py` — PDF, image OCR, DOCX extraction
- [ ] `app/routers/upload.py` — multipart file upload
- [ ] `app/services/transcription.py` — faster-whisper STT
- [ ] `app/routers/transcribe.py` — voice transcription endpoint
- [ ] Modify ChatView.jsx for file upload + voice transcription
- [ ] Create FilePreview.jsx component

### Phase 3: RAG Pipeline
**Milestone: LLM cites specific medical sources in responses**

- [ ] `app/services/embedding_service.py` — sentence-transformers
- [ ] `app/services/rag_service.py` — ChromaDB retrieval
- [ ] Medical system prompt + RAG prompt templates
- [ ] Document ingestion scripts
- [ ] Integrate RAG into chat endpoint
- [ ] SourceCitations.jsx component

### Phase 4: Reasoning / Agent Mode
**Milestone: Toggle Normal vs Reasoning mode in chat**

- [ ] `app/services/reasoning_service.py` — agentic orchestrator (Groq/Gemini)
- [ ] SSE events for live reasoning steps
- [ ] Mode toggle in ChatView UI
- [ ] Graceful fallback when no API key

### Phase 5: Fine-Tuning
**Milestone: Custom fine-tuned model in Ollama**

- [ ] MedLLM_FineTune_QLoRA.ipynb (Colab notebook)
- [ ] Modelfile for Ollama
- [ ] RAG_Evaluation.ipynb

### Phase 6: Profile, History, Polish
**Milestone: Complete polished application**

- [ ] Profile + History API endpoints
- [ ] Auth context + streaming message components
- [ ] Docker compose
- [ ] README with architecture diagram
