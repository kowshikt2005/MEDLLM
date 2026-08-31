# Reproducible Grounded RAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` for inline task-by-task execution. Do not use subagents for this repository.

**Goal:** Make MedLLM’s normal chat reproducible with a configurable, verified local Ollama model, an auditable curated corpus, and retrieved-source-or-abstain behavior.

**Architecture:** Normal chat receives an optional selected Ollama model, verifies it against the local Ollama inventory, retrieves evidence from Chroma, and only calls the model when evidence qualifies. A JSON manifest and immutable source snapshots drive a batched index-rebuild command. The existing Groq reasoning path stays untouched; its default configured Ollama model remains separate from the normal-mode selector.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, Ollama Python client, ChromaDB, sentence-transformers, pytest, React, Vite.

**Spec:** `docs/superpowers/specs/2026-08-31-medllm-closure-design.md`

## Global Constraints

- Keep QLoRA files and `backend/app/services/reasoning_service.py` unchanged.
- Never restore or select `medllama:latest`; the initial local baseline is the already-installed `mistral:latest`, verified against Ollama model ID `6577803aa9a0` and blob SHA-256 `f5074b1221da0f5a2910d33b642efa5b9eb58cfdddca1c79e16d7ad28aa2b31f`.
- Support other installed Ollama chat models, but label them as not matching the recorded baseline.
- Do not download models or invoke Groq during automated tests.
- Keep user uploads local and out of the checked-in permanent corpus. Retrieved user-upload chunks may be cited as user-provided sources when attached to a chat request.
- Do not make medical-accuracy, currentness, or confidence claims.
- Do not stage, commit, push, create a PR, tag, release, or alter remote state.

---

### Task 1: Add test infrastructure and the local-runtime contract

**Files:**
- Create: `backend/requirements-dev.txt`
- Create: `backend/pytest.ini`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_runtime_service.py`
- Create: `backend/app/services/runtime_service.py`
- Modify: `backend/app/config.py`

**Interfaces:**
- Produces `RuntimeModel(name: str, identifier: str | None)` and `RuntimeStatus(ollama_available: bool, selected_model: str, selected_model_available: bool, selected_model_matches_baseline: bool | None, models: list[RuntimeModel], message: str | None)`.
- Produces `inspect_runtime(client: object, selected_model: str, baseline_identifier: str | None) -> RuntimeStatus`.
- Consumes an Ollama-compatible object exposing `list()`; tests pass a fake object and never contact Ollama.

- [ ] **Step 1: Write failing runtime tests**

```python
class FakeClient:
    def __init__(self, response):
        self.response = response

    def list(self):
        return self.response


def test_inspect_runtime_reports_configured_model_and_baseline_match():
    status = inspect_runtime(
        FakeClient({"models": [{"name": "mistral:latest", "digest": "6577803aa9a0"}]}),
        "mistral:latest",
        "6577803aa9a0",
    )
    assert status.ollama_available is True
    assert status.selected_model_available is True
    assert status.selected_model_matches_baseline is True


def test_inspect_runtime_reports_connection_failure():
    class OfflineClient:
        def list(self):
            raise ConnectionError("offline")

    status = inspect_runtime(OfflineClient(), "mistral:latest", None)
    assert status.ollama_available is False
    assert "Ollama" in status.message
```

- [ ] **Step 2: Run the new test file and verify it fails because the service does not exist**

Run: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_runtime_service.py -v`

Expected: collection error for `app.services.runtime_service`.

- [ ] **Step 3: Add the minimal runtime service and configuration fields**

```python
@dataclass(frozen=True)
class RuntimeModel:
    name: str
    identifier: str | None


def inspect_runtime(client: object, selected_model: str, baseline_identifier: str | None) -> RuntimeStatus:
    try:
        raw_models = getattr(client.list(), "models", None) or client.list().get("models", [])
    except Exception:
        return RuntimeStatus(False, selected_model, False, None, [], "Ollama is unavailable.")
```

Set `Settings.ollama_model` to `mistral:latest`, add `ollama_baseline_identifier`, and document that Pydantic environment values may override the default.

- [ ] **Step 4: Run the runtime tests and full backend test suite**

Run: `backend\.venv\Scripts\python.exe -m pytest backend\tests -v`

Expected: all tests pass without an Ollama server.

- [ ] **Step 5: Review the unstaged task diff**

Run: `git diff -- backend/app/config.py backend/app/services/runtime_service.py backend/tests backend/requirements-dev.txt backend/pytest.ini`

Expected: only runtime contract and test-infrastructure changes. Do not stage or commit.

### Task 2: Expose selected-model health and use it in normal chat

**Files:**
- Create: `backend/app/routers/runtime.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/models/schemas.py`
- Modify: `backend/app/services/llm_service.py`
- Modify: `backend/app/routers/chat.py`
- Modify: `frontend/src/services/api.js`
- Modify: `frontend/src/components/ChatView.jsx`
- Test: `backend/tests/test_runtime_router.py`

**Interfaces:**
- `GET /api/runtime` returns `RuntimeStatus` for `settings.ollama_model`.
- `ChatRequest` gains `model: str | None = None`.
- `LLMService.chat_stream(messages, system_prompt, model: str | None = None)` uses the validated selected model for normal mode.
- `chatStream(message, { model })` serializes `model` as JSON.

- [ ] **Step 1: Write failing endpoint and chat-preflight tests**

```python
def test_runtime_endpoint_returns_inventory(client, monkeypatch):
    monkeypatch.setattr(runtime_service, "inspect_configured_runtime", lambda: READY)
    response = client.get("/api/runtime")
    assert response.status_code == 200
    assert response.json()["selected_model_available"] is True


def test_normal_chat_emits_error_before_generation_when_selected_model_is_missing(monkeypatch):
    monkeypatch.setattr(runtime_service, "inspect_runtime", lambda *args: MISSING_MODEL)
    events = collect_sse(chat(ChatRequest(message="What is diabetes?", model="missing"), fake_db))
    assert events[0]["type"] == "error"
    assert "not installed" in events[0]["content"]
```

- [ ] **Step 2: Run the tests and verify the runtime route and error event are absent**

Run: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_runtime_router.py -v`

Expected: FAIL because `/api/runtime` and preflight behavior do not exist.

- [ ] **Step 3: Implement the API, normal-mode preflight, and model selector**

```python
@router.get("/runtime")
def get_runtime() -> RuntimeStatus:
    return inspect_configured_runtime()

selected_model = request.model or settings.ollama_model
status = inspect_runtime(llm_service.client, selected_model, settings.ollama_baseline_identifier)
if not status.selected_model_available:
    yield json.dumps({"type": "error", "content": status.message})
    yield json.dumps({"type": "done", "content": "", "sources": []})
    return
```

Add a compact normal-mode model `<select>` populated from `/api/runtime`; send its value through `api.chatStream`. Keep reasoning mode’s existing call path unchanged.

- [ ] **Step 4: Run backend tests and frontend production build**

Run: `backend\.venv\Scripts\python.exe -m pytest backend\tests -v`

Expected: all backend tests pass.

Run: `npm run build`

Working directory: `frontend`

Expected: Vite finishes with exit code 0.

- [ ] **Step 5: Review the unstaged task diff**

Run: `git diff -- backend/app/main.py backend/app/models/schemas.py backend/app/services/llm_service.py backend/app/routers/chat.py backend/app/routers/runtime.py frontend/src/services/api.js frontend/src/components/ChatView.jsx backend/tests/test_runtime_router.py`

Expected: only selected-model runtime behavior; no reasoning-service changes. Do not stage or commit.

### Task 3: Add the curated source manifest and deterministic index rebuild

**Files:**
- Create: `backend/knowledge_base/manifest.json`
- Create: `backend/knowledge_base/sources/cdc_diabetes_basics.txt`
- Create: `backend/knowledge_base/sources/cdc_diabetes_symptoms.txt`
- Create: `backend/knowledge_base/sources/cdc_high_blood_pressure.txt`
- Create: `backend/knowledge_base/SOURCE_NOTICE.md`
- Create: `backend/scripts/build_curated_index.py`
- Create: `backend/tests/test_curated_index.py`
- Modify: `backend/app/services/rag_service.py`
- Modify: `.gitignore`

**Interfaces:**
- `load_manifest(path: Path) -> list[SourceRecord]` validates IDs, relative source paths, URLs, SHA-256 values, and snapshot bytes.
- `build_curated_index(manifest_path: Path, batch_size: int, writer: Callable) -> BuildSummary` passes chunk metadata with `corpus_id`, `source_id`, `title`, `url`, `sha256`, and `chunk_index` to `rag_service.add_documents`.
- `--replace-curated` deletes only records where `corpus_id == "cdc-diabetes-hypertension-2026-08"`; it never deletes uploads or an entire Chroma directory.

- [ ] **Step 1: Write failing manifest and batching tests**

```python
def test_manifest_rejects_changed_snapshot(tmp_path):
    manifest = write_manifest(tmp_path, sha256="0" * 64)
    with pytest.raises(ManifestValidationError, match="checksum"):
        load_manifest(manifest)


def test_build_batches_stable_chunk_metadata(tmp_path):
    writes = []
    summary = build_curated_index(valid_manifest(tmp_path), batch_size=1, writer=writes.append)
    assert summary.source_count == 1
    assert writes[0].metadatas[0]["source_id"] == "cdc-diabetes-basics"
```

- [ ] **Step 2: Run the test file and verify it fails because the builder does not exist**

Run: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_curated_index.py -v`

Expected: import failure for `build_curated_index`.

- [ ] **Step 3: Add snapshots, manifest, source notice, and non-interactive builder**

```json
{
  "corpus_id": "cdc-diabetes-hypertension-2026-08",
  "sources": [{
    "id": "cdc-diabetes-basics",
    "path": "sources/cdc_diabetes_basics.txt",
    "title": "Diabetes Basics",
    "url": "https://www.cdc.gov/diabetes/about/",
    "retrieved_at": "2026-08-31",
    "sha256": "<computed snapshot hash>"
  }]
}
```

The command prints verified files, created chunks, output collection, and failures. It must require `--replace-curated` before removing prior curated records and use existing upload metadata unchanged.

- [ ] **Step 4: Run index-builder tests and a dry manifest check**

Run: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_curated_index.py -v`

Expected: all manifest and batching tests pass without downloading embeddings.

Run: `backend\.venv\Scripts\python.exe scripts\build_curated_index.py --verify-only`

Working directory: `backend`

Expected: three source hashes verify and no Chroma collection changes occur.

- [ ] **Step 5: Review the unstaged task diff**

Run: `git diff -- backend/knowledge_base backend/scripts/build_curated_index.py backend/app/services/rag_service.py backend/tests/test_curated_index.py .gitignore`

Expected: permanent source snapshots and a safe rebuild path; no generated index is tracked. Do not stage or commit.

### Task 4: Gate normal answers on retrieved evidence and show traceable citations

**Files:**
- Create: `backend/app/services/evidence_service.py`
- Create: `backend/tests/test_evidence_service.py`
- Modify: `backend/app/prompts/medical.py`
- Modify: `backend/app/routers/chat.py`
- Modify: `backend/app/services/rag_service.py`
- Modify: `frontend/src/components/SourceCitations.jsx`
- Modify: `frontend/src/components/ChatView.jsx`

**Interfaces:**
- `ABSTENTION_TEXT` is a fixed message used when normal-mode retrieval returns no qualifying chunks.
- `build_grounded_prompt(rag_sources: list[dict]) -> str` instructs the model to use only listed excerpts and cite `[source_id]`.
- Each returned source includes `title`, `url`, `source_id`, `chunk_index`, and `relevance`.

- [ ] **Step 1: Write failing evidence and source-metadata tests**

```python
def test_no_evidence_returns_fixed_abstention():
    assert response_for_sources([]) == ABSTENTION_TEXT


def test_prompt_forbids_general_knowledge_fallback():
    prompt = build_grounded_prompt([SOURCE])
    assert "only the supplied excerpts" in prompt
    assert "general knowledge" not in prompt


def test_search_returns_traceable_source_metadata(fake_collection, monkeypatch):
    result = rag_service.search("diabetes", n_results=1)
    assert result[0]["source_id"] == "cdc-diabetes-basics"
    assert result[0]["url"].startswith("https://")
```

- [ ] **Step 2: Run the tests and verify the old general-knowledge fallback fails them**

Run: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_evidence_service.py -v`

Expected: FAIL because evidence service and traceable metadata do not exist.

- [ ] **Step 3: Implement normal-mode abstention and source metadata**

```python
rag_sources = rag_service.search(request.message, n_results=3)
if not rag_sources:
    full_response = ABSTENTION_TEXT
    yield json.dumps({"type": "token", "content": full_response})
    yield json.dumps({"type": "done", "content": "", "sources": []})
    return
```

Replace the clinical-copilot prompt identity and the general-knowledge fallback with source-only instructions. Render each source as a title linked to its URL, plus `Relevance: NN%`; do not use confidence colors or terminology.

- [ ] **Step 4: Run evidence tests, full backend tests, and frontend build**

Run: `backend\.venv\Scripts\python.exe -m pytest backend\tests -v`

Expected: all tests pass.

Run: `npm run build`

Working directory: `frontend`

Expected: Vite finishes with exit code 0.

- [ ] **Step 5: Review the unstaged task diff**

Run: `git diff -- backend/app/services/evidence_service.py backend/app/prompts/medical.py backend/app/routers/chat.py backend/app/services/rag_service.py frontend/src/components/SourceCitations.jsx frontend/src/components/ChatView.jsx backend/tests/test_evidence_service.py`

Expected: normal mode is evidence-gated and citations are traceable; reasoning service remains unchanged. Do not stage or commit.

### Task 5: Add scanned-PDF fallback and test every retained ingestion path

**Files:**
- Modify: `backend/app/services/document_processor.py`
- Modify: `backend/app/routers/upload.py`
- Create: `backend/tests/test_document_processor.py`
- Create: `backend/tests/test_upload_router.py`

**Interfaces:**
- `_extract_pdf(file_path: str) -> str` uses embedded page text when present and OCRs only pages without embedded text.
- `extract_text(file_path, file_type)` returns an empty string on failure; upload returns an explicit failure response and does not index an empty extraction.

- [ ] **Step 1: Write failing extraction and upload tests**

```python
def test_pdf_uses_ocr_for_page_without_embedded_text(monkeypatch):
    monkeypatch.setattr(document_processor.pdfplumber, "open", fake_pdf_with_blank_page)
    monkeypatch.setattr(document_processor.pytesseract, "image_to_string", lambda image: "scanned text")
    assert "scanned text" in document_processor._extract_pdf("scan.pdf")


def test_upload_does_not_index_empty_extraction(monkeypatch, client):
    monkeypatch.setattr(upload, "extract_text", async_returning(""))
    response = client.post("/api/upload", files={"file": ("empty.pdf", b"bytes", "application/pdf")})
    assert response.status_code == 422
```

- [ ] **Step 2: Run the tests and verify the current PDF and upload behavior fails them**

Run: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_document_processor.py backend\tests\test_upload_router.py -v`

Expected: FAIL because blank PDF pages have no OCR fallback and uploads index no-text files.

- [ ] **Step 3: Implement fallback and explicit extraction failure**

```python
page_text = page.extract_text() or ""
if page_text.strip():
    text_parts.append(page_text)
else:
    image = page.to_image(resolution=300).original
    ocr_text = pytesseract.image_to_string(image).strip()
    if ocr_text:
        text_parts.append(ocr_text)
```

Return HTTP 422 before calling `chunk_text` or `rag_service.add_documents` when extraction is empty. Keep DOCX, image OCR, text, and OpenAI Whisper routes unchanged.

- [ ] **Step 4: Run retained-ingestion tests and full backend suite**

Run: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_document_processor.py backend\tests\test_upload_router.py -v`

Expected: PDF fallback and empty-file protection tests pass.

Run: `backend\.venv\Scripts\python.exe -m pytest backend\tests -v`

Expected: all tests pass without Tesseract, Whisper, Ollama, Chroma embeddings, or Groq installed/running.

- [ ] **Step 5: Review the unstaged task diff**

Run: `git diff -- backend/app/services/document_processor.py backend/app/routers/upload.py backend/tests/test_document_processor.py backend/tests/test_upload_router.py`

Expected: only extraction safety and tests; no transcription or reasoning changes. Do not stage or commit.

### Task 6: Record baseline provenance, retire invalid benchmark artifacts, and perform local acceptance checks

**Files:**
- Create: `backend/model-provenance.json`
- Create: `backend/scripts/check_model_provenance.py`
- Modify: `README.md`
- Modify: `PLAN.md`
- Delete: `backend/scripts/benchmark_medqa.py`
- Delete: `backend/data/benchmark_results/groq_llama-3.3-70b-versatile_20260329_163956.json`
- Delete: `backend/data/benchmark_results/mistral_20260329_163147.json`
- Delete: `backend/data/benchmark_results/ollama_medllama_latest_20260418_110049.json`
- Delete: `backend/data/chroma_db_backup_20260417_214112/`
- Test: `backend/tests/test_model_provenance.py`

**Interfaces:**
- `model-provenance.json` records `model: "mistral:latest"`, expected model identifier, blob SHA-256, architecture source, local verification date, and a `functional_smoke_test` field.
- `check_model_provenance.py` exits nonzero when the installed model name or identifier does not match the record; it does not download, change, or run a model.

- [ ] **Step 1: Write failing provenance tests**

```python
def test_provenance_check_accepts_matching_local_inventory(tmp_path):
    result = validate_provenance(record("mistral:latest", "6577803aa9a0"), FakeClient("mistral:latest", "6577803aa9a0"))
    assert result.matches is True


def test_provenance_check_rejects_changed_latest_tag():
    result = validate_provenance(record("mistral:latest", "6577803aa9a0"), FakeClient("mistral:latest", "different"))
    assert result.matches is False
```

- [ ] **Step 2: Run the test and verify it fails before the provenance checker exists**

Run: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_model_provenance.py -v`

Expected: import failure for provenance validation.

- [ ] **Step 3: Implement provenance check, then remove exact obsolete artifacts**

```json
{
  "model": "mistral:latest",
  "ollama_model_id": "6577803aa9a0",
  "blob_sha256": "f5074b1221da0f5a2910d33b642efa5b9eb58cfdddca1c79e16d7ad28aa2b31f",
  "source": "local Ollama inventory",
  "functional_smoke_test": "pending"
}
```

Before each deletion, list and verify the exact tracked path. Remove only the three named result JSON files, the legacy benchmark script, and the exact stale Chroma backup directory; leave `backend/data/uploads/` untouched.

- [ ] **Step 4: Run provenance tests and local acceptance checks**

Run: `backend\.venv\Scripts\python.exe -m pytest backend\tests -v`

Expected: all tests pass.

Run: `backend\.venv\Scripts\python.exe scripts\check_model_provenance.py`

Working directory: `backend`

Expected: reports the local Mistral ID match without model download or inference.

Run: `npm run build`

Working directory: `frontend`

Expected: Vite finishes with exit code 0.

- [ ] **Step 5: Review the final unstaged diff and exact deletion set**

Run: `git diff --check && git status --short`

Expected: only approved source, test, documentation, provenance, and explicitly named deletion changes. Do not stage or commit.

## Plan self-review

- Spec coverage: Tasks 1–2 implement runtime selection and checks; Task 3 implements curated sources and index rebuilding; Task 4 implements grounded normal chat and traceable citations; Task 5 preserves and validates multimodal ingestion; Task 6 records the selected baseline and removes invalid artifacts.
- Placeholder scan: no undecided implementation branches remain. Model downloading and Groq calls are explicitly excluded from tests.
- Type consistency: `RuntimeStatus` is returned by the runtime router and consumed by the model selector; `ChatRequest.model` is passed by `chatStream` to `LLMService.chat_stream`; curated metadata keys are produced by the builder and returned by `rag_service.search`.
