# MedLLM

MedLLM is a FastAPI and React desktop application for experimenting with local LLM chat, document retrieval, and multimodal text extraction.

## Current capabilities

- Local chat through any installed Ollama completion model, selected in normal mode or with `OLLAMA_MODEL`.
- ChromaDB retrieval using sentence-transformers and cross-encoder reranking.
- PDF, DOCX, image-OCR, and text-file ingestion.
- Browser-recorded audio transcribed locally with OpenAI Whisper.
- Optional reasoning mode: Groq plans and synthesizes; Ollama and Chroma handle focused retrieval steps.
- Server-Sent Events for streamed replies and source labels with retrieval-relevance scores.

## Scope and limitations

- Normal mode answers only when retrieved source excerpts support the question; otherwise it returns a clear abstention without calling the chat model.
- Source labels show retrieval relevance, not factual certainty or a confidence score.
- The optional reasoning mode sends the question and generated research summaries to Groq; it remains a separate cloud-assisted experiment rather than the normal evidence-gated path.
- The repository does not publish a medical-accuracy benchmark or a currentness guarantee.
- The legacy `medllama:latest` default is not supplied. Set `OLLAMA_MODEL` to a locally installed Ollama chat model.
- Three SHA-256-pinned CDC source cards cover diabetes and high blood pressure. The generated Chroma index is local and is not tracked in Git.

## Run locally

Requirements: Python 3.11+, Node.js 18+, Ollama, and Tesseract for image/scanned-PDF OCR.

1. Copy `backend/.env.example` to `backend/.env`, then set `OLLAMA_MODEL` to an exact model shown by `ollama list`.
2. In `backend`, create and activate a Python virtual environment, install `requirements.txt`, and run `python -m uvicorn app.main:app --reload`. Confirm the selected model is available at `http://localhost:8000/api/runtime`.
3. In `frontend`, run `npm install` and `npm run dev`.
4. Open `http://localhost:5173`.

The first use of Whisper, sentence-transformers, or the reranker can download their model files. Install the Tesseract desktop binary before using image or scanned-PDF OCR. Groq is optional; leave `GROQ_API_KEY` unset to use normal mode only.

## Model provenance

`backend/model-provenance.json` records the locally observed `mistral:latest` baseline identifier, blob digest, configuration, and license. It is a reproducibility record, not a performance or medical-quality result. Normal mode may use another installed Ollama completion model, but that choice should be recorded and checked under a controlled local evaluation before becoming a new baseline.

## Curated corpus

The initial corpus is limited to three attributed CDC source cards on diabetes and high blood pressure. Verify their pinned content, then build or replace only the generated curated Chroma chunks:

```powershell
cd backend
python scripts/build_curated_index.py --verify-only
python scripts/build_curated_index.py --replace-curated
```

The rebuild preserves user-uploaded chunks because it deletes only records marked `corpus=curated`. Review the original CDC pages before changing a source card, update its manifest digest, and rebuild. The cards are educational summaries with direct source links, not a claim that the app provides medical reliability.

## Project layout

```text
frontend/                  React and Vite interface
backend/app/               FastAPI routes, services, prompts, and models
backend/app/services/      Ollama, retrieval, documents, and transcription
backend/scripts/           One-off maintenance and evaluation scripts
PLAN.md                    Current roadmap
CHANGELOG.md               Historical implementation notes
```

## Next checks

1. Select any new local model only after recording its provenance and controlled local evaluation results.
2. Run a manual desktop smoke test for model selection, grounded answers, abstention, source links, uploads, and scanned-PDF OCR.
3. Expand the curated corpus only through reviewed source cards with updated hashes and rebuild evidence.

The repository includes a QLoRA exploration notebook. It does not include a trained adapter, GGUF export, Modelfile, or reproducible fine-tuning result.
## Local runtime troubleshooting

If Ollama reports `llama runner process has terminated` on Windows, this checkout includes `backend/scripts/start_ollama_stable.ps1` for selecting a stable GPU backend or CPU fallback. This is runtime troubleshooting only; it does not establish model quality.