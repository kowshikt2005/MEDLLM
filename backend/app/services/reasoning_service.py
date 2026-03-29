"""
Reasoning service — agentic multi-step orchestration using Groq + RAG + Mistral.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHY TWO MODELS?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Groq (LLaMA 70B, free API)   — the "brain"
    - 70 billion parameters, much better at reasoning and synthesis
    - Used for: planning sub-questions, synthesizing the final answer
    - Runs on Groq's cloud, so no local hardware requirements

  Mistral 7B (local, via Ollama) — the "researcher"
    - Used for: answering each focused sub-question using RAG context
    - Runs locally, private, no cost
    - Fast enough for focused single-topic answers

  Together they produce more thorough, better-structured answers than
  either model alone.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PIPELINE (3 STEPS)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  User: "Can diabetes cause kidney disease and how do I prevent it?"

  Step 1 — PLAN (Groq)
    Break into: ["How does diabetes damage kidneys?",
                 "What are the stages of diabetic nephropathy?",
                 "How can you prevent kidney disease in diabetics?"]

  Step 2 — RESEARCH (RAG + Mistral, once per sub-question)
    For each sub-question:
      → Search ChromaDB for relevant medical chunks
      → Build focused system prompt
      → Call local Mistral 7B for the answer
      → Collect answer + sources

  Step 3 — SYNTHESIZE (Groq, streaming)
    Feed Groq all 3 sub-question answers
    → Groq writes a comprehensive, structured final response
    → Streamed token by token to the browser

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SSE EVENTS YIELDED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  {"type": "step",     "content": "Analyzing question..."}  → shown in UI
  {"type": "step",     "content": "Researching (1/2): ..."}  → shown in UI
  {"type": "token",    "content": "Based on the..."}         → streamed to message
  {"type": "_sources", "content": [...]}                     → internal, caught by chat.py

The "_sources" event is NEVER sent to the browser. chat.py intercepts it
and puts the sources into the final "done" SSE event instead.
"""

import json
from collections.abc import AsyncGenerator

from groq import AsyncGroq

from app.config import settings
from app.prompts.medical import build_system_prompt
from app.services import rag_service
from app.services.llm_service import llm_service

# This is the internal sentinel event type.
# chat.py looks for this and strips it before forwarding events to the browser.
SOURCES_SENTINEL = "_sources"


async def reason_stream(
    query: str,
    attachment_context: str = "",
    image_descriptions: list[str] | None = None,
) -> AsyncGenerator[str, None]:
    """
    Full agentic reasoning pipeline.

    This is an async generator — it yields JSON-encoded strings, one at a time.
    Each string is an SSE event that chat.py either forwards to the browser
    or intercepts (for the _sources sentinel).

    Args:
        query:               The user's original chat message.
        attachment_context:  Extracted text from uploaded files (Phase 2).
                             Injected into each sub-question's system prompt
                             so the LLM can reason about uploaded documents
                             even in reasoning mode.
        image_descriptions:  Moondream visual descriptions of uploaded images.

    Yields:
        JSON strings — step events, token events, and the _sources sentinel.
    """
    client = AsyncGroq(api_key=settings.groq_api_key)

    # ── Step 1: PLAN ─────────────────────────────────────────────────────
    # Ask Groq (70B) to break the question into focused sub-questions.
    # We use a low temperature (0.2) because we want consistent, logical
    # decomposition, not creative variation.

    yield json.dumps({"type": "step", "content": "Analyzing your question..."})

    sub_questions = [query]  # fallback if planning fails

    try:
        plan_response = await client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a medical reasoning assistant. "
                        "Your job is to break complex medical questions into 2-3 focused sub-questions. "
                        "Respond with ONLY a valid JSON array of strings — no markdown, no explanation, no code fences.\n"
                        'Example output: ["What causes high blood pressure?", "What are its long-term complications?"]'
                    ),
                },
                {
                    "role": "user",
                    "content": f"Break this medical question into 2-3 focused sub-questions:\n\n{query}",
                },
            ],
            temperature=0.2,
        )

        raw = plan_response.choices[0].message.content.strip()

        # Groq sometimes wraps the JSON in ```json ... ``` markdown fences.
        # Strip those if present.
        if "```" in raw:
            parts = raw.split("```")
            # parts[1] is the content between the first pair of fences
            raw = parts[1].strip()
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()

        parsed = json.loads(raw)

        if isinstance(parsed, list) and len(parsed) > 0:
            # Cap at 3 sub-questions — more would add too much latency
            sub_questions = [str(q) for q in parsed[:3]]

    except Exception as e:
        # JSON parse error or API error — log so it's visible in the uvicorn console
        print(f"[Reasoning] Planning step failed: {type(e).__name__}: {e}")
        yield json.dumps({
            "type": "step",
            "content": "Planning step skipped — researching question directly.",
        })

    yield json.dumps({
        "type": "step",
        "content": f"Identified {len(sub_questions)} sub-question(s) to research",
    })

    # ── Step 2: RESEARCH ─────────────────────────────────────────────────
    # For each sub-question: search ChromaDB for relevant chunks,
    # then call local Mistral 7B to answer using that context.
    #
    # Why use Mistral here instead of Groq?
    #   - Mistral is local and private (no data leaves your machine)
    #   - The sub-questions are focused enough that a 7B model handles them well
    #   - Groq's free tier has rate limits; we save it for planning and synthesis

    sub_answers = []
    all_sources = []

    for i, sq in enumerate(sub_questions, start=1):
        yield json.dumps({
            "type": "step",
            "content": f"Researching ({i}/{len(sub_questions)}): {sq}",
        })

        # RAG retrieval for this specific sub-question
        # n_results=2 keeps the context focused; more chunks = more noise
        rag_chunks = rag_service.search(sq, n_results=2)
        all_sources.extend(rag_chunks)

        # Build the system prompt for this sub-question.
        # attachment_context is passed through so uploaded files (PDFs, images)
        # are available to the LLM even in reasoning mode — fixes the silent
        # "attachments ignored in reasoning mode" bug.
        sub_system_prompt = build_system_prompt(
            rag_sources=rag_chunks,
            attachment_context=attachment_context,
            image_descriptions=image_descriptions,
        )

        # Call local Mistral — blocking but acceptable for single-user dev
        answer = await llm_service.chat(
            messages=[{"role": "user", "content": sq}],
            system_prompt=sub_system_prompt,
        )

        sub_answers.append({"question": sq, "answer": answer})

    yield json.dumps({"type": "step", "content": "Synthesizing all findings into a final answer..."})

    # Deduplicate sources across all sub-questions.
    # If the same file was retrieved for multiple sub-questions, show it once.
    # Keep the highest score if a source appears multiple times.
    source_scores: dict[str, float] = {}
    for s in all_sources:
        if s["score"] > 0.6:  # same threshold as rag_service
            existing = source_scores.get(s["source"], 0)
            source_scores[s["source"]] = max(existing, s["score"])

    unique_sources = [
        {"source": src, "score": round(score, 3)}
        for src, score in source_scores.items()
    ]

    # ── Step 3: SYNTHESIZE ───────────────────────────────────────────────
    # Feed Groq all the sub-question answers and ask it to write
    # a comprehensive, well-structured response to the original question.
    # We stream this so the user sees tokens appearing as Groq generates them.

    sub_qa_block = "\n\n".join([
        f"Sub-question {i + 1}: {sa['question']}\nResearched answer: {sa['answer']}"
        for i, sa in enumerate(sub_answers)
    ])

    synthesis_messages = [
        {
            "role": "system",
            "content": (
                "You are MedLLM, a knowledgeable and compassionate medical AI assistant. "
                "You have been given research findings from multiple sub-questions. "
                "Synthesize them into a clear, comprehensive, well-structured answer. "
                "Use headings (##) and bullet points. "
                "Note any uncertainties and always recommend professional medical consultation."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Original question: {query}\n\n"
                f"Research findings:\n{sub_qa_block}\n\n"
                "Based on these findings, write a comprehensive answer to the original question. "
                "Be thorough but clear. Flag uncertainties. Recommend when to see a doctor."
            ),
        },
    ]

    # Use the async context manager form for streaming.
    # This ensures the HTTP connection is properly closed after streaming,
    # even if an exception occurs mid-stream (resource leak fix for groq >= 0.13).
    async with client.chat.completions.stream(
        model=settings.groq_model,
        messages=synthesis_messages,
        temperature=0.4,
    ) as stream:
        async for chunk in stream:
            token = chunk.choices[0].delta.content or ""
            if token:
                yield json.dumps({"type": "token", "content": token})

    # ── Sentinel: pass sources back to chat.py ────────────────────────────
    # This is NOT forwarded to the browser. chat.py intercepts it and
    # puts the sources into the final "done" event.
    yield json.dumps({"type": SOURCES_SENTINEL, "content": unique_sources})
