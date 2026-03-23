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

### What's Next (remaining Phase 1 items)

- [ ] Install backend dependencies (pip install — had Windows file lock issues)
- [ ] Test backend starts (`uvicorn app.main:app --reload`)
- [ ] Test auth endpoints (signup + login via `/docs`)
- [ ] Test chat streaming end-to-end (frontend → backend → Ollama → frontend)
- [ ] Verify frontend still builds (`npm run dev` from `frontend/`)
