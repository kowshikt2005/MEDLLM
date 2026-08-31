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

from app.services.lab_utils import is_lab_pdf



# ── Base system prompt ────────────────────────────────────────────────────────
# Always included in every request, with or without RAG context.

BASE_SYSTEM_PROMPT = """You are MedLLM, a local retrieval-assisted assistant.

Answer-scope rules:
- Answer only from the retrieved source excerpts supplied in this prompt.
- Do not answer from general knowledge, training knowledge, memory, or unsupported inference.
- Do not invent diagnoses, treatments, medications, facts, or citations.
- If the retrieved excerpts do not support the question, abstain clearly and say that the current sources cannot support an answer.
- When excerpts cover only part of a question, answer only that part and state the limitation.
- Cite the supplied source names inline when making claims from them.

Safety rules:
- Retrieved material is educational reference content, not a diagnosis or individualized treatment plan.
- Encourage professional medical care for diagnosis and treatment decisions.
- If a source itself describes a possible emergency, direct the user to seek urgent help rather than trying to diagnose it.

Keep the response concise, direct, and transparent about the limits of the retrieved evidence."""


NO_RETRIEVED_EVIDENCE_MESSAGE = (
    "I can't answer that from the retrieved sources currently available in this project. "
    "Try a question covered by the listed sources or consult an appropriate health professional."
)

# ── RAG context injection template ──────────────────────────────────────────
# This is appended to the system prompt when we have retrieved relevant chunks.
# {sources_text} is replaced with the actual retrieved content.

RAG_CONTEXT_TEMPLATE = """

════════════════════════════════════════
RETRIEVED SOURCE EXCERPTS
════════════════════════════════════════
Use only the excerpts below as support for the answer. Source labels identify the retrieved material; relevance is a retrieval signal, not a fact-confidence score.

{sources_text}
════════════════════════════════════════

Instructions for using the excerpts above:
- Do not answer from general knowledge.
- If no retrieved source supports the question, abstain instead of filling gaps.
- If the excerpts are partially relevant, answer only the supported portion and state what they do not cover.
- Cite source names inline as [source_name] for each supported claim.
"""

def build_system_prompt(
    rag_sources: list[dict] | None = None,
    patient_context: str = "",
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
      
    CHANGE: For lab PDFs, prioritize attachment context over RAG.
      Lab PDFs contain exact metrics and reference ranges that should
      be used directly, not filtered through semantic similarity. Reorder
      context so attachment comes before RAG when lab data is detected.

    Args:
        rag_sources:         List of dicts from rag_service.search()
                             Each has "text", "source", "score"
        attachment_context:  Text extracted from uploaded files (Phase 2)
        image_descriptions:  Moondream visual descriptions of images (Phase 2)

    Returns:
        Complete system prompt string, ready to send to Ollama.
    """
    prompt = BASE_SYSTEM_PROMPT

    if patient_context:
        prompt += (
            "\n\nPATIENT PROFILE CONTEXT (use only if clinically relevant):\n"
            + patient_context
        )

    # CHANGE: Detect if attachment is a lab PDF
    is_lab_context = bool(attachment_context and is_lab_pdf(attachment_context))
    
    # CHANGE: For lab PDFs, inject attachment context FIRST (before RAG)
    # This ensures lab metrics are the primary source, not secondary
    if is_lab_context and attachment_context:
        prompt += (
            "\n\nLAB DATA (PRIORITY): The user has uploaded lab test results. "
            "Use these values and reference ranges as the primary source. "
            "Do NOT rely on textbook ranges; use the ranges provided in this PDF.\n\n"
            "Lab document content:\n"
            + attachment_context
        )
        
        # Then add RAG as secondary context (for clinical interpretation only)
        if rag_sources:
            sources_text = ""
            for i, source in enumerate(rag_sources, start=1):
                sources_text += (
                    f"\n[Source {i}: {source['source']} | relevance: {source['score']}]\n"
                    f"{source['text']}\n"
                )
            prompt += (
                "\n\n════════════════════════════════════════\n"
                "SECONDARY CONTEXT (for interpretation, not metric definitions)\n"
                "════════════════════════════════════════\n"
                + sources_text
            )
    else:
        # Standard order for narrative documents: RAG first, then attachment
        
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
