# MedLLM Closure Design

Status: approved scope recorded locally; no Git commit or remote action is authorized.

## Goal

Make the existing desktop application reproducible and evidence-oriented while preserving its multimodal paths, QLoRA notebook, and optional reasoning mode.

## Decisions

- The permanent starter corpus covers diabetes and hypertension only.
- It contains text-only snapshots of three official CDC pages: Diabetes Basics, Symptoms of Diabetes, and About High Blood Pressure. Each source records its URL, retrieval date, SHA-256 checksum, attribution, and a non-endorsement notice. Images, logos, and third-party-marked material are excluded.
- Chroma remains the retrieval store. Generated indexes are local and ignored by Git; a command rebuilds them from the checked-in manifest and source snapshots.
- The application supports any installed Ollama chat model selected through configuration. It must check that Ollama is available and that the selected model is installed before accepting a chat. `medllama:latest` is retired and will not be restored.
- Normal mode stays local. The optional Groq reasoning architecture is retained unchanged and remains cloud-dependent when enabled.
- When retrieval has no qualifying evidence, chat returns a fixed abstention response. When it does, answers expose source metadata and retrieval relevance; relevance is not labelled as confidence.
- PDF, DOCX, image OCR, and local OpenAI Whisper audio remain supported. PDF extraction adds OCR fallback only when no embedded text is found.
- QLoRA code, its notebook, and the reasoning-mode orchestration are not rewritten.

## Planned changes

1. Runtime and configuration
   - Remove the hard-coded retired-model default.
   - Add an installed-model discovery endpoint and a selected-model startup check.
   - Add concise runtime/setup documentation and a model-provenance record for the model evaluated locally.

2. Curated corpus and index
   - Add the three CDC text snapshots and a versioned source manifest.
   - Add a deterministic, batched build-index command with hashes, chunk metadata, and clear failure reporting.
   - Leave user uploads local and out of the permanent corpus and Git history.

3. Grounded retrieval
   - Remove the general-knowledge fallback from the medical prompt.
   - Require a qualifying retrieval result before generation; otherwise abstain.
   - Return title, source URL, chunk identifier, and relevance alongside a reply.

4. Multimodal and interface accuracy
   - Preserve all existing upload/audio routes.
   - Add scanned-PDF OCR fallback and clear user-facing extraction failures.
   - Keep Groq reasoning unchanged; label cloud use and fallback accurately.

5. Tests and cleanup
   - Add backend tests for model checks, manifest validation, index creation, extraction, retrieval, citations, and abstention.
   - Remove obsolete benchmark results and stale Chroma backup artifacts after the replacement index workflow is verified.
   - Do not publish a medical-accuracy claim.

## Acceptance criteria

- A clean clone can configure an installed Ollama model, build the CDC corpus index, and see the documented chunk count and source hashes.
- A supported diabetes or hypertension question returns citations from the curated corpus.
- An unsupported query abstains instead of using general knowledge.
- Missing Ollama or a missing selected model yields an actionable error before generation.
- PDF, DOCX, OCR-image, scanned-PDF, and audio routes have automated coverage where dependencies can be stubbed.
- Documentation distinguishes local normal chat from optional cloud reasoning and names OpenAI Whisper correctly.
- The implementation is verified locally, remains unstaged and uncommitted, and is reported for user review before any Git action.

## Non-goals

- No QLoRA training, model download, adapter export, or restoration of `medllama:latest`.
- No redesign of Groq reasoning mode.
- No hosted service, account system, background job platform, or unlimited-corpus performance claim.
- No commit, push, pull request, tag, release, or remote-state change.
