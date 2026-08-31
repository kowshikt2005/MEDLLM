# MedLLM roadmap

`README.md` is the current project overview; `CHANGELOG.md` is historical context only.

## Current local closure state

- Normal chat uses an installed Ollama model, checks availability before generation, and never selects retired `medllama:latest`.
- The starter corpus is three SHA-256-pinned CDC source cards for diabetes and high blood pressure. Its rebuild replaces only `corpus=curated` chunks.
- Normal mode answers only from retrieved excerpts or gives a deterministic abstention. Citations expose retrieval relevance and original source links.
- PDF extraction falls back to Tesseract only for pages without selectable text.
- The QLoRA exploration notebook and optional Groq reasoning architecture remain unchanged.

## Next manual checks

1. Record controlled local evaluation evidence before promoting another Ollama model to a baseline.
2. Manually smoke-test the desktop flow, including model selection, source links, abstention, uploads, and scanned PDFs.
3. Review source pages and hashes before expanding the small curated corpus.

## Not in scope

- Restoring or recommending `medllama:latest`.
- Publishing a medical-accuracy benchmark or currentness guarantee.
- Reworking the QLoRA notebook or optional reasoning-mode architecture.
