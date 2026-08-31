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
import asyncio
import time
import re
from collections.abc import AsyncGenerator

from groq import AsyncGroq

from app.config import settings
from app.prompts.medical import build_system_prompt
from app.services import rag_service
from app.services.llm_service import llm_service
from app.services.lab_utils import is_lab_pdf, extract_lab_tests, format_lab_summary, CRITICAL_VALUES

# This is the internal sentinel event type.
# chat.py looks for this and strips it before forwarding events to the browser.
SOURCES_SENTINEL = "_sources"


def _is_low_signal_answer(text: str) -> bool:
    """Detect generic/non-grounded assistant filler that should not drive fallback synthesis."""
    value = (text or "").strip().lower()
    if not value:
        return True
    if len(value) < 25:
        return True

    low_signal_markers = [
        "please provide",
        "i can help you",
        "as a medical expert system",
        "cannot generate a response",
        "not enough information",
        "insufficient information",
        "let me know",
    ]
    return any(marker in value for marker in low_signal_markers)


def _normalize_research_answer(answer: str) -> str:
    """Replace low-quality research outputs with an explicit insufficiency marker."""
    if _is_low_signal_answer(answer):
        return "[Insufficient grounded evidence for this sub-question from retrieved context.]"
    return answer.strip()


def _detect_lab_context(attachment_context: str) -> bool:
    """
    Check if the attachment contains lab data.
    
    Returns True if the attachment appears to be a lab report.
    """
    return bool(attachment_context and is_lab_pdf(attachment_context))


def _extract_labs_from_attachment(attachment_context: str) -> list[dict]:
    """
    Extract structured lab tests from attachment context.
    
    Returns list of test dicts with lab data, or empty list if not a lab PDF.
    """
    if not attachment_context or not is_lab_pdf(attachment_context):
        return []
    
    tests = extract_lab_tests(attachment_context)
    return [t.to_dict() for t in tests]


def _build_lab_specific_subquestions(attachment_context: str) -> list[str]:
    """
    Generate lab-specific sub-questions instead of generic medical questions.
    
    For lab PDFs, asks focused questions about:
      1. Extracting all test values and reference ranges
      2. Identifying abnormal values
      3. Determining clinical significance
    """
    # Check for critical values to add urgency if needed
    tests = extract_lab_tests(attachment_context)
    critical_tests = [t for t in tests if t.abnormality_type == "CRITICAL"]
    
    sub_questions = [
        "Extract all test names, values, units, and reference ranges from the PDF",
        "Which test values fall outside their normal reference ranges?",
    ]
    
    # Add critical value question if any found
    if critical_tests:
        sub_questions.append(
            "Which values are critically abnormal and require immediate attention?"
        )
    
    sub_questions.append(
        "What is the clinical significance of these abnormal findings?"
    )
    
    return sub_questions[:3]  # Cap at 3 sub-questions


def _format_lab_fallback(attachment_context: str) -> str:
    """
    Generate a deterministic lab fallback response as a structured table.
    
    When synthesis times out on lab data, return a simple, clear table
    with all extracted lab values and their status.
    """
    tests = extract_lab_tests(attachment_context)
    if not tests:
        return ""
    
    lines = [
        "\n## Lab Results Summary\n",
        "| Test | Value | Unit | Reference | Status |",
        "|------|-------|------|-----------|--------|",
    ]
    
    for test in tests:
        # Determine status with emojis and color coding
        if test.abnormality_type == "CRITICAL":
            status = "🚨 CRITICAL - Seek immediate medical attention"
        elif test.is_abnormal:
            status = "⚠️ ABNORMAL - Review with provider"
        else:
            status = "✓ Normal"
        
        lines.append(
            f"| {test.test_name} | {test.value} | {test.unit} | "
            f"{test.reference_range} | {status} |"
        )
    
    # Add clinical notes for critical values
    critical_tests = [t for t in tests if t.abnormality_type == "CRITICAL"]
    if critical_tests:
        lines.append("\n### Critical Values Requiring Action:")
        for test in critical_tests:
            # Add specific clinical context for known critical values
            context = _get_critical_value_context(test.test_name, test.value)
            if context:
                lines.append(f"- **{test.test_name}** ({test.value} {test.unit}): {context}")
    
    return "\n".join(lines)


def _get_critical_value_context(test_name: str, value_str: str) -> str:
    """
    Provide clinical context for specific critical values.
    
    Hard-coded mappings for common critical lab values.
    """
    test_lower = test_name.lower()
    
    try:
        value = float(value_str)
    except (ValueError, TypeError):
        return ""
    
    context_map = {
        "b12": "B12 < 200 pmol/L is severe deficiency; risk of neuropathy and cognitive symptoms",
        "vitamin d": "Vitamin D < 20 ng/mL is severe deficiency; increases fracture risk and affects immunity",
        "glucose": "Extreme glucose levels can cause seizures or stroke; requires immediate intervention",
        "potassium": "Abnormal potassium affects heart rhythm; arrhythmias can be life-threatening",
        "sodium": "Severe hyponatremia/hypernatremia can cause cerebral edema or seizures",
        "hemoglobin": "Severe anemia (Hgb < 5) requires urgent transfusion to avoid organ damage",
        "creatinine": "Severely elevated creatinine suggests acute or advanced chronic kidney disease",
        "alt": "Severely elevated ALT suggests acute liver injury or hepatitis",
        "ast": "Severely elevated AST suggests acute liver injury or muscle damage",
    }
    
    for key, ctx in context_map.items():
        if key in test_lower:
            return ctx
    
    return ""



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
    start_ts = time.monotonic()

    async def _step(content: str) -> AsyncGenerator[str, None]:
        """Emit a step event with optional elapsed-time metadata."""
        if settings.reasoning_verbose_output:
            elapsed = time.monotonic() - start_ts
            content = f"[{elapsed:0.1f}s] {content}"
        yield json.dumps({"type": "step", "content": content})

    # ── Step 1: PLAN ─────────────────────────────────────────────────────
    # Ask Groq (70B) to break the question into focused sub-questions.
    # We use a low temperature (0.2) because we want consistent, logical
    # decomposition, not creative variation.
    #
    # CHANGE: If attachment is a lab report, use lab-specific sub-questions
    # instead of generic Groq planning.

    async for event in _step(
        "Analyzing your question with Groq planning model "
        f"({settings.groq_model}, timeout={settings.reasoning_plan_timeout_seconds}s)..."
    ):
        yield event

    sub_questions = [query]  # fallback if planning fails
    is_lab_pdf_context = _detect_lab_context(attachment_context)
    
    # CHANGE: Use lab-specific sub-questions if attachment is a lab PDF
    if is_lab_pdf_context:
        async for event in _step("Detected lab report; using lab-specific analysis questions."):
            yield event
        sub_questions = _build_lab_specific_subquestions(attachment_context)
    else:
        # Standard Groq planning for narrative documents
        try:
            plan_response = await asyncio.wait_for(
                client.chat.completions.create(
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
                ),
                timeout=settings.reasoning_plan_timeout_seconds,
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
            async for event in _step("Planning step skipped; researching original question directly."):
                yield event

    async for event in _step(
        f"Identified {len(sub_questions)} sub-question(s) to research."
    ):
        yield event
    if settings.reasoning_verbose_output:
        async for event in _step("Planned sub-questions: " + " | ".join(sub_questions)):
            yield event

    # ── Step 2: RESEARCH ─────────────────────────────────────────────────
    # For each sub-question: search ChromaDB for relevant chunks,
    # then call local Mistral 7B to answer using that context.
    #
    # Why use Mistral here instead of Groq?
    #   - Mistral is local and private (no data leaves your machine)
    #   - The sub-questions are focused enough that a 7B model handles them well
    #   - Groq's free tier has rate limits; we save it for planning and synthesis
    #
    # CHANGE: For lab PDFs, skip RAG and use direct PDF content instead

    sub_answers = []
    all_sources = []

    for i, sq in enumerate(sub_questions, start=1):
        async for event in _step(
            f"Researching ({i}/{len(sub_questions)}): {sq} "
            f"[timeout={settings.reasoning_research_timeout_seconds}s]"
        ):
            yield event

        # CHANGE: Skip RAG retrieval for lab sub-questions
        # Use direct PDF content instead for more accurate extraction
        if is_lab_pdf_context:
            rag_chunks = []  # No RAG needed for lab data
            async for event in _step(
                "Using direct PDF extraction (no RAG needed for lab metrics)."
            ):
                yield event
        else:
            # RAG retrieval for this specific sub-question
            # n_results=2 keeps the context focused; more chunks = more noise
            rag_chunks = rag_service.search(sq, n_results=2)
            all_sources.extend(rag_chunks)
            if settings.reasoning_verbose_output:
                source_preview = ", ".join([
                    f"{c['source']} ({c['score']:.3f})" for c in rag_chunks[:2]
                ]) or "no sources"
                async for event in _step(
                    f"Retrieved {len(rag_chunks)} context chunk(s): {source_preview}"
                ):
                    yield event

        # Build the system prompt for this sub-question.
        # attachment_context is passed through so uploaded files (PDFs, images)
        # are available to the LLM even in reasoning mode — fixes the silent
        # "attachments ignored in reasoning mode" bug.
        sub_system_prompt = build_system_prompt(
            rag_sources=rag_chunks,
            attachment_context=attachment_context,
            image_descriptions=image_descriptions,
        )

        # Use Groq for the focused research step (more accurate than local 7B)
        try:
            sub_response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=settings.groq_model,
                    messages=[
                        {"role": "system", "content": sub_system_prompt},
                        {"role": "user", "content": sq},
                    ],
                    temperature=getattr(settings, "llm_temperature", 0.1),
                    max_tokens=1024,
                ),
                timeout=settings.reasoning_research_timeout_seconds,
            )

            answer = sub_response.choices[0].message.content
        except TimeoutError:
            answer = (
                "[Timed out while researching this sub-question. "
                "Proceeding with partial findings.]"
            )
            async for event in _step(
                f"Research timed out for sub-question {i}; continuing with partial results."
            ):
                yield event
        except Exception as e:
            answer = f"[Research step failed: {type(e).__name__}: {e}]"
            async for event in _step(
                f"Research failed for sub-question {i}; continuing with partial results."
            ):
                yield event

        answer = _normalize_research_answer(answer)
        sub_answers.append({"question": sq, "answer": answer})
        if settings.reasoning_verbose_output:
            answer_state = "insufficient" if answer.startswith("[Insufficient") else "grounded"
            async for event in _step(
                f"Completed sub-question {i}: answer status={answer_state}."
            ):
                yield event

    async for event in _step(
        "Synthesizing findings into final answer with streaming output "
        f"[timeout={settings.reasoning_synthesis_timeout_seconds}s]."
    ):
        yield event

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
                "You are MedLLM, a clinician-facing medical copilot. "
                "You have been given research findings from multiple sub-questions. "
                "Synthesize them into a concise clinical answer for a licensed clinician. "
                "Use headings: Assessment, Initial Approach, Escalation / Red Flags. "
                "Use concise bullets where helpful. "
                "State uncertainty explicitly and avoid layperson counseling tone unless requested."
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
    synthesized_any_token = False

    async def _stream_synthesis() -> None:
        nonlocal synthesized_any_token
        async with client.chat.completions.stream(
            model=settings.groq_model,
            messages=synthesis_messages,
            temperature=0.4,
        ) as stream:
            async for chunk in stream:
                token = chunk.choices[0].delta.content or ""
                if token:
                    synthesized_any_token = True
                    yield json.dumps({"type": "token", "content": token})

    synthesis_started = time.monotonic()
    try:
        stream_iter = _stream_synthesis().__aiter__()
        heartbeat = max(2, settings.reasoning_progress_heartbeat_seconds)
        while True:
            elapsed = time.monotonic() - synthesis_started
            remaining = settings.reasoning_synthesis_timeout_seconds - elapsed
            if remaining <= 0:
                raise TimeoutError

            wait_window = min(heartbeat, remaining)
            try:
                event = await asyncio.wait_for(stream_iter.__anext__(), timeout=wait_window)
                yield event
            except asyncio.TimeoutError:
                async for step_event in _step(
                    "Synthesis still in progress; waiting for model tokens..."
                ):
                    yield step_event
            except StopAsyncIteration:
                break
    except TimeoutError:
        async for event in _step("Synthesis timed out; returning partial research summary."):
            yield event
    except Exception as e:
        print(f"[Reasoning] Synthesis step failed: {type(e).__name__}: {e}")
        async for event in _step("Synthesis failed; returning partial research summary."):
            yield event

    if not synthesized_any_token:
        # CHANGE: For lab PDFs, use deterministic fallback table format
        if is_lab_pdf_context:
            async for event in _step("Generating structured lab results table..."):
                yield event
            
            lab_fallback = _format_lab_fallback(attachment_context)
            if lab_fallback:
                yield json.dumps({"type": "token", "content": lab_fallback})
                synthesized_any_token = True
        
        # If not lab or lab fallback failed, use standard fallback
        if not synthesized_any_token:
            async for event in _step("Generating grounded fallback summary from available findings..."):
                yield event

            local_fallback_prompt = (
                "Original question:\n"
                f"{query}\n\n"
                "Research findings (some may be insufficient):\n"
                f"{sub_qa_block}\n\n"
                "Write a concise clinician-facing answer with sections: "
                "Assessment, Initial Approach, Escalation / Red Flags. "
                "Use ONLY the provided findings. "
                "Do NOT ask the user for additional information. "
                "If evidence is weak, state that explicitly."
            )

            fallback_text = ""
            try:
                fallback_text = await asyncio.wait_for(
                    llm_service.chat(
                        messages=[{"role": "user", "content": local_fallback_prompt}],
                        system_prompt=(
                            "You are MedLLM fallback synthesizer. "
                            "Be clinically concise and grounded to given findings."
                        ),
                    ),
                    timeout=settings.reasoning_local_fallback_timeout_seconds,
                )
                if _is_low_signal_answer(fallback_text):
                    fallback_text = ""
            except Exception:
                fallback_text = ""

        if not fallback_text:
            fallback_lines = [
                "Assessment:",
                "- Full synthesis could not be completed in time.",
                "- Findings are partial and may be insufficient for definitive conclusions.",
                "Initial Approach:",
            ]
            for idx, sa in enumerate(sub_answers, start=1):
                fallback_lines.append(f"- Sub-question {idx}: {sa['question']}")
                fallback_lines.append(f"  Finding: {sa['answer']}")
            fallback_lines.append("Escalation / Red Flags:")
            fallback_lines.append("- If urgent symptoms are present, escalate to immediate in-person care.")
            fallback_text = "\n".join(fallback_lines)

        yield json.dumps({"type": "token", "content": fallback_text})

    async for event in _step("Reasoning pipeline complete; returning final sources."):
        yield event

    # ── Sentinel: pass sources back to chat.py ────────────────────────────
    # This is NOT forwarded to the browser. chat.py intercepts it and
    # puts the sources into the final "done" event.
    yield json.dumps({"type": SOURCES_SENTINEL, "content": unique_sources})
