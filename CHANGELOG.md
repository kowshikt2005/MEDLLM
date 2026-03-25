# MedLLM — Changelog & Implementation Log

## Phase 1: Backend Foundation + Text Chat (In Progress)

### Date: 2026-03-23

### What was done

Restructured the project from a frontend-only React app into a full-stack monorepo with a FastAPI backend, and wired the frontend to talk to the backend via SSE streaming.

---

### Project Restructure

**Moved all frontend files into `frontend/` subdirectory using `git mv`:**
```
Before:                    After:
MEDLLM/                    MEDLLM/
├── src/                   ├── frontend/
├── package.json           │   ├── src/
├── vite.config.ts         │   ├── package.json
├── tailwind.config.js     │   ├── vite.config.ts
├── ...                    │   ├── tailwind.config.js
                           │   ├── node_modules/
                           │   └── ...
                           ├── backend/
                           │   └── ...
                           ├── PLAN.md
                           ├── CHANGELOG.md
                           └── README.md
```

---

### Backend Files Created

All under `backend/`:

| File | Purpose |
|---|---|
| `app/__init__.py` | Makes `app` a Python package |
| `app/config.py` | pydantic-settings config — reads from `.env` or uses defaults. Holds: database URL, Ollama host/model, JWT secret, Groq key (optional), Whisper model, ChromaDB path |
| `app/main.py` | FastAPI entry point — CORS middleware (allows localhost:5173), registers auth + chat routers, lifespan event calls `init_db()`, `/api/health` endpoint |
| `app/models/__init__.py` | Package init |
| `app/models/database.py` | SQLAlchemy async models + SQLite engine. Tables: `users`, `health_profiles`, `conversations`, `messages`, `attachments`, `feedback`. Provides `get_db()` dependency and `init_db()` |
| `app/models/schemas.py` | Pydantic request/response schemas: `SignupRequest`, `LoginRequest`, `TokenResponse`, `UserResponse`, `ChatRequest`, `MessageResponse`, `ConversationResponse`, `HealthProfileRequest`, `UploadResponse` |
| `app/services/__init__.py` | Package init |
| `app/services/llm_service.py` | Ollama client wrapper. `chat_stream()` yields tokens one at a time (async generator). `chat()` returns full response. `is_available()` health check. Error handling yields error text instead of crashing |
| `app/routers/__init__.py` | Package init |
| `app/routers/auth.py` | `/api/auth/signup` and `/api/auth/login`. bcrypt password hashing via passlib. JWT token creation/verification via python-jose. `get_current_user()` dependency (defined but not yet wired to chat endpoint) |
| `app/routers/chat.py` | `/api/chat` — SSE streaming endpoint. Creates conversation, saves user message, streams tokens from Ollama via `EventSourceResponse`, saves assistant response, sends "done" event with conversation_id |
| `app/prompts/__init__.py` | Package init |
| `requirements.txt` | Phase 1 deps: fastapi, uvicorn, python-multipart, pydantic-settings, sqlalchemy, aiosqlite, python-jose[cryptography], passlib[bcrypt], ollama, sse-starlette. Phases 2-4 commented out |
| `.env.example` | Template showing all env vars with placeholder values |

**Empty directories created:** `data/knowledge_base/`, `scripts/`, `uploads/`

---

### Frontend Files Created

| File | Purpose |
|---|---|
| `frontend/src/services/api.js` | Centralized API client. Token management via localStorage (`medllm_token`, `medllm_user`). Functions: `login()`, `signup()`, `logout()`, `isLoggedIn()`, `chatStream()`, `healthCheck()`. `chatStream()` reads SSE via `ReadableStream` and calls `onToken`/`onStep`/`onDone`/`onError` callbacks |

---

### Frontend Files Modified

**`frontend/src/App.jsx`:**
- Added `import { api } from './services/api'`
- Changed `useState(false)` to `useState(api.isLoggedIn())` — checks localStorage for existing token so refresh doesn't log you out
- Added `handleLogout()` function that calls `api.logout()`

**`frontend/src/components/AuthView.jsx`:**
- Added `import { api } from "../services/api"`
- Added `isLoading` and `serverError` state variables
- Replaced `handleSubmit`: was `console.log() + onLogin()`, now calls `api.login()` or `api.signup()` with try/catch, stores token, then calls `onLogin()`
- Added server error display (`<p className="text-red-500">`) above both form submit buttons
- Added `disabled={isLoading}` to submit buttons
- Login button shows "LOGGING IN..." / Signup shows "SIGNING UP..." while loading

**`frontend/src/components/ChatView.jsx`:**
- Added `import { api } from "../services/api"`
- Added `conversationId` state (tracks current conversation for follow-up messages)
- Added `isStreaming` state (prevents double-send while LLM is responding)
- Changed initial greeting from "Medicare Assistant" to "MedLLM Assistant"
- Replaced `handleSendMessage()` entirely:
  - Was: `setTimeout` → hardcoded "Thank you" response
  - Now: Adds empty assistant message to UI, calls `api.chatStream()` with `onToken` callback that appends each token to the last message via `setMessages((prev) => ...)` functional update
  - `onDone` saves `conversationId` for follow-up messages
  - `onError` shows error text in assistant message bubble
- Send button: disabled when `isStreaming`, shows spinner animation instead of Send icon

**`frontend/vite.config.ts`:**
- Added `server.proxy` config: `/api` requests forwarded to `http://localhost:8000`

---

### Root Files Created/Modified

| File | Action |
|---|---|
| `PLAN.md` | Created — full implementation plan with 6 phases and checkboxes |
| `CHANGELOG.md` | Created — this file |
| `.gitignore` | Updated — added Python (`__pycache__`, `venv/`, `*.pyc`), backend data (`chroma_db/`, `medllm.db`, `uploads/`), `.env` files |

---

### Bugs Found & Fixed During Audit

1. **`schemas.py` — unused `EmailStr` import** removed. `EmailStr` requires `email-validator` package which isn't installed. We use plain `str` for email fields (frontend already validates).

2. **`chat.py` — missing `user_id` on Conversation creation.** `Conversation` table has `user_id` as `nullable=False`, but the chat endpoint wasn't setting it. Fixed by adding `user_id="anonymous"` as placeholder. Will be replaced with real user ID when auth is wired to chat in Phase 6.

3. **Noted (not fixed):** `llm_service.py` uses synchronous `ollama.Client.chat()` inside async generator. This blocks the event loop during generation. Acceptable for Phase 1 (single user), but should be moved to a thread pool (`asyncio.to_thread`) if concurrent users are needed.

---

### How to Run (after installing dependencies)

**Backend:**
```bash
cd backend
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux
pip install fastapi uvicorn python-multipart pydantic-settings sqlalchemy aiosqlite "python-jose[cryptography]" "passlib[bcrypt]" ollama sse-starlette
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install    # if not already done
npm run dev
```

**Ollama** (must be running separately):
```bash
ollama run mistral
```

**Verify:** Visit `http://localhost:8000/api/health` and `http://localhost:8000/docs`

---

### Phase 1 Completion — 2026-03-25

- [x] Install backend dependencies (pinned versions + greenlet fix)
- [x] Test backend starts (`uvicorn app.main:app --reload`)
- [x] Test auth endpoints (signup + login)
- [x] Test chat streaming end-to-end (frontend → backend → Ollama → frontend)
- [x] Verify frontend still builds (`npm run dev` from `frontend/`)

**Issues resolved during setup:**
- pip backtracking: fixed by pinning all versions with `==` instead of `>=`
- WinError 32 file lock: fixed by purging pip cache + `--no-cache-dir`
- Missing `greenlet`: added to requirements — required by SQLAlchemy async mode
- `passlib` + `bcrypt` 5.0 incompatibility: pinned `bcrypt==4.1.3`

**Phase 1 — COMPLETE**

---

## Phase 2: Multimodal Input Pipeline

### Date: 2026-03-25

### What Was Done

Added real multimodal capabilities to MedLLM — document processing (PDF, DOCX), image understanding (Tesseract OCR + moondream vision model), and speech-to-text (OpenAI Whisper). Files upload on selection (not on send), so text extraction happens in the background while the user types their question.

---

### Design Decisions

**1. Upload-before-send pattern**
Files are uploaded immediately when selected. The backend extracts text and creates an `Attachment` row with `message_id = NULL`. When the user hits send, the chat endpoint looks up those attachments by ID, links them to the newly created message, and injects their text into the LLM system prompt. This hides extraction latency behind the user's typing time.

**2. `Attachment.message_id` made nullable**
The original schema had `nullable=False` on `message_id`. This was changed to `nullable=True` to support the upload-before-send pattern — attachments exist in the DB before any message exists to link them to.
> **Action required on schema change:** Delete `backend/data/medllm.db` so `init_db()` recreates the table with the new nullable column. SQLAlchemy does not auto-migrate existing databases.

**3. `openai-whisper` instead of `faster-whisper`**
The original plan specified `faster-whisper` (a CTranslate2-based port of Whisper). Switched to `openai-whisper` because `faster-whisper` requires CTranslate2, which has a complex build chain on Windows and was likely to cause install failures. `openai-whisper` installs cleanly via pip on Windows.

**4. Dual image processing**
Images go through two separate processes:
- **Tesseract OCR** — extracts any text visible in the image (e.g. prescription labels, lab report photos, whiteboard text)
- **moondream** — Ollama vision model that describes what the image depicts visually

Both results are injected into the system prompt. This gives the LLM both "what text is in this image" and "what does this image show."

**5. Attachment text injected into system prompt (not user message)**
Extracted document text is appended to the system prompt under a clearly delimited section:
```
--- Attached file: blood_report.pdf ---
[extracted text]
--- End of blood_report.pdf ---
```
Keeping it in the system prompt (not the user message) separates the document context from the user's actual question, which produces cleaner LLM reasoning.

**6. Whisper model lazy loading**
The Whisper model (~1.5GB for "small") is not loaded at server startup. It's loaded on the first transcription request and kept in memory for subsequent requests. This keeps server startup fast.

---

### Files Created

| File | Purpose |
|------|---------|
| `backend/app/services/document_processor.py` | Text extraction: PDF via pdfplumber, DOCX via python-docx, images via Tesseract OCR, text files via direct read. `detect_file_type()` maps extensions to type strings |
| `backend/app/routers/upload.py` | `POST /api/upload` — saves file to `data/uploads/`, calls document_processor, creates Attachment row, returns `upload_id` |
| `backend/app/services/transcription.py` | Whisper STT with lazy model loading. Includes `_ensure_ffmpeg_on_path()` to auto-detect winget portable ffmpeg install on Windows |
| `backend/app/routers/transcribe.py` | `POST /api/transcribe` — accepts audio blob, saves to temp file, transcribes, cleans up temp file, returns `TranscriptionResponse` |
| `frontend/src/components/FilePreview.jsx` | Attachment chip UI — shows filename, file-type icon, upload status (spinner/checkmark/error), remove button. Receives `attachments` array and `onRemove` callback as props |

---

### Files Modified

| File | Change |
|------|--------|
| `backend/requirements.txt` | Uncommented Phase 2 packages; replaced `faster-whisper>=1.0.3` with `openai-whisper>=20231117` |
| `backend/app/models/database.py` | `Attachment.message_id` → `nullable=True` |
| `backend/app/models/schemas.py` | Added `TranscriptionResponse(BaseModel)` with `text: str` and `language: str \| None` |
| `backend/app/main.py` | Imported and registered `upload.router` and `transcribe.router` |
| `backend/app/routers/chat.py` | Added attachment processing: fetches attachments by ID, links to message, injects extracted_text into system prompt, calls moondream for images via `ollama.chat()` with base64-encoded image |
| `frontend/src/services/api.js` | Added `uploadFile(file)` and `transcribeAudio(audioBlob)` — both use `FormData` (not JSON) for binary file upload |
| `frontend/src/components/ChatView.jsx` | Real file upload on selection (replaces alert placeholder); real Whisper transcription on voice stop (replaces hardcoded string); `attachments` state with temp ID pattern; `isTranscribing` state; FilePreview component rendered above input; attachment IDs passed to `chatStream()` |

---

### Problems Encountered & Fixes

**Problem 1: ffmpeg not found (`FileNotFoundError: [WinError 2]`)**
- **Root cause:** Whisper calls `ffmpeg` as a subprocess to decode audio files. `winget install ffmpeg` performs a "portable" install (zip extraction), which does NOT add the binary to the system PATH. The backend server starts with the old PATH and can't find `ffmpeg.exe`.
- **Fix:** Added `_ensure_ffmpeg_on_path()` in `transcription.py` that runs at module import time. It uses `glob` to search `%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\**\bin` and prepends the found path to `os.environ["PATH"]`. This patches the PATH for the running process and all its subprocesses (including the ffmpeg call) without touching system settings.
- **Key insight:** `os.environ["PATH"]` changes are process-local — they affect only the Python process and its children, not the terminal or system.

**Problem 2: JSX syntax error — multiple elements in ternary branch**
- **Root cause:** The recording UI uses a ternary (`isRecording ? <RecordingUI/> : <InputUI/>`). The non-recording branch had three sibling elements added (transcription indicator, FilePreview, input div) without a wrapper.
- **Fix:** Wrapped in a React fragment (`<>...</>`) so the ternary branch returns a single root element.

**Problem 3: `faster-whisper` skipped**
- **Root cause:** `faster-whisper` depends on CTranslate2 which has Windows-specific build issues.
- **Fix:** Switched to `openai-whisper` before any install attempt. No user impact.

**Non-error Warning: FP16 not supported on CPU**
```
UserWarning: FP16 is not supported on CPU; using FP32 instead
```
- This is informational only, not an error. Whisper prefers FP16 (half-precision) for speed on CUDA GPUs. On CPU it falls back to FP32. Transcription works correctly, just takes a few extra seconds.
- **No fix needed.**

---

### Prerequisites (manual user steps)

These must be done before Phase 2 works:

| Step | Command | Notes |
|------|---------|-------|
| Install Phase 2 Python packages | `pip install -r requirements.txt` | In venv |
| Install Tesseract OCR binary | Download from UB-Mannheim GitHub | Windows `.exe` installer. Must be on system PATH |
| Pull moondream vision model | `ollama pull moondream` | ~1.7GB download |
| Install ffmpeg | `winget install ffmpeg` | Handled automatically in code via `_ensure_ffmpeg_on_path()` |
| Delete old database | Delete `backend/data/medllm.db` | Required after `nullable=True` change on `message_id` |
| Whisper model download | Automatic on first transcription | ~1.5GB for "small" model, downloaded to `~/.cache/whisper/` |

---

### Known Limitations & Backlog

**1. Context window cap (32K tokens)**
Mistral 7B supports ~32K tokens. Very large PDFs (50+ pages) could exceed this limit, causing Ollama to truncate or error. Phase 3 (RAG) fixes this by only injecting the most relevant document chunks into the prompt rather than the full text.

**2. Orphaned attachments**
If a user uploads a file but never sends a message (closes the tab, navigates away), an `Attachment` row with `message_id = NULL` remains in the database and the file stays on disk in `data/uploads/`. There is no cleanup job. A future improvement would be a periodic cleanup task that deletes attachments older than X hours that still have `message_id = NULL`.

**3. Whisper blocks the async event loop**
`model.transcribe()` is synchronous and CPU-bound. Calling it directly in an `async def` endpoint blocks the entire FastAPI event loop for the duration of transcription (typically 3-10 seconds for short clips). This is acceptable for single-user local dev but would degrade performance under concurrent requests. Fix: wrap in `asyncio.to_thread(transcribe, tmp.name)`. (Same issue exists for `llm_service.py` — noted in Phase 1 backlog.)

**4. No file size limit on uploads**
The `/api/upload` endpoint accepts files of any size. A very large PDF could cause high memory usage during pdfplumber extraction. A `max_size` check should be added to the upload endpoint (e.g. reject files > 20MB).

**5. moondream must be pulled manually**
The chat endpoint silently catches moondream errors and includes a failure note in the prompt. If `ollama pull moondream` was not run, image visual analysis silently degrades to OCR-only. A startup check (similar to the Ollama health check) could warn if moondream is missing.

**6. `user_id` still hardcoded as `"anonymous"`**
Inherited from Phase 1. Chat conversations are not linked to real users. Phase 6 will wire the JWT token to `get_current_user()` and use the real `user_id`.

**7. `UploadResponse.extracted_text` always returns full text**
The schema returns the complete extracted text in the upload response. For large documents this means sending potentially thousands of words back to the frontend (which doesn't display it). A future improvement: return only a short preview (e.g. first 200 chars) in the response and keep the full text server-side.

---

### How to Run (Phase 2)

**Backend:**
```bash
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm run dev
```

**Ollama (must be running):**
```bash
ollama serve   # if not already running as a service
```

**Verification checklist:**
- [ ] Upload a PDF → FilePreview chip shows filename with checkmark → send a question about it → LLM answers using document content
- [ ] Upload an image with text → OCR extracts text + moondream describes the image → LLM responds about both
- [ ] Upload a `.docx` → text extracted → LLM discusses document content
- [ ] Click mic → speak → stop → real transcribed text appears in input (not hardcoded string)
- [ ] Transcription failure message appears if backend is unreachable

**Phase 2 — COMPLETE**
