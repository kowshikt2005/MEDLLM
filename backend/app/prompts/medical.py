"""
Medical system prompts and RAG context templates.

WHY A SEPARATE PROMPTS FILE?
  Prompts are code — they directly control LLM behavior.
  Keeping them here (not scattered across routers) means:
    1. Easy to improve prompts without touching business logic
    2. Easy to compare old vs. new prompts
    3. One place to look when "why is the LLM saying X"

HOW PROMPTS WORK WITH OLLAMA:
  The chat API accepts a list of messages:
    [{"role": "system", "content": "..."},
     {"role": "user",   "content": "What is diabetes?"}]

  The "system" message sets the LLM's behavior, persona, and constraints
  for the ENTIRE conversation. It's the most important part of prompt engineering.

  The RAG context (retrieved document chunks) is injected INTO the system
  message — not as a separate user message — because it represents background
  knowledge the assistant "already knows", not something the user said.
"""


# ── Base system prompt ────────────────────────────────────────────────────────
# Always included in every request, with or without RAG context.

BASE_SYSTEM_PROMPT = """You are MedLLM, a knowledgeable and compassionate medical AI assistant.

Guidelines:
- Provide accurate, evidence-based medical information
- Use clear, understandable language while maintaining medical accuracy
- Always recommend consulting healthcare professionals for diagnosis and treatment
- If you are uncertain about something, say so rather than guessing
- Structure your responses with headings and bullet points when appropriate
- When answering from provided context, always cite the source document name

IMPORTANT: You are an AI assistant, not a licensed doctor. Always recommend professional medical consultation for diagnosis, treatment, and medication decisions."""


# ── RAG context injection template ──────────────────────────────────────────
# This is appended to the system prompt when we have retrieved relevant chunks.
# {sources_text} is replaced with the actual retrieved content.

RAG_CONTEXT_TEMPLATE = """

════════════════════════════════════════
MEDICAL KNOWLEDGE BASE CONTEXT
════════════════════════════════════════
The following excerpts are from verified medical reference documents.
Use these to inform your answer and cite them by source name.

{sources_text}
════════════════════════════════════════

Instructions for using the context above:
- If the question is answered by the context, base your response on it and cite the source
- If the context is only partially relevant, use it for what it covers and note the limitation
- If the context is not relevant to the question, say so and answer from general knowledge
- Always indicate whether your answer is from the provided sources or general knowledge"""


def build_system_prompt(
    rag_sources: list[dict] | None = None,
    attachment_context: str = "",
    image_descriptions: list[str] | None = None,
) -> str:
    """
    Assemble the complete system prompt from all available context.

    This is the single function that chat.py calls. It combines:
      1. BASE_SYSTEM_PROMPT (always)
      2. RAG context (if relevant chunks were found in ChromaDB)
      3. Uploaded file content (if user attached files — from Phase 2)
      4. Image descriptions (if user uploaded images — from Phase 2)

    The order matters:
      - Base prompt first sets the persona and rules
      - RAG context next (most authoritative source)
      - User-uploaded files last (most specific to the current question)

    Args:
        rag_sources:         List of dicts from rag_service.search()
                             Each has "text", "source", "score"
        attachment_context:  Text extracted from uploaded files (Phase 2)
        image_descriptions:  Moondream visual descriptions of images (Phase 2)

    Returns:
        Complete system prompt string, ready to send to Ollama.
    """
    prompt = BASE_SYSTEM_PROMPT

    # ── 1. Inject RAG context ──────────────────────────────────────────────
    if rag_sources:
        sources_text = ""
        for i, source in enumerate(rag_sources, start=1):
            sources_text += (
                f"\n[Source {i}: {source['source']} | relevance: {source['score']}]\n"
                f"{source['text']}\n"
            )
        prompt += RAG_CONTEXT_TEMPLATE.format(sources_text=sources_text)

    # ── 2. Inject uploaded file content (Phase 2) ─────────────────────────
    if attachment_context:
        prompt += (
            "\n\nThe user has attached the following files. "
            "Use this content to answer their question:"
            + attachment_context
        )

    # ── 3. Inject image descriptions (Phase 2) ────────────────────────────
    if image_descriptions:
        for desc in image_descriptions:
            prompt += desc

    return prompt
