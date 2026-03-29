"""
Chat router — the core endpoint that connects the frontend to the LLM.

How streaming works end-to-end:
  1. Browser sends POST /api/chat with {"message": "...", "mode": "normal"|"reasoning"}
  2. This endpoint creates an SSE (Server-Sent Events) response
  3. For each token/step the LLM generates, we send an SSE event to the browser
  4. The browser's ReadableStream reads each event and updates the UI
  5. When done, we send a final "done" event with conversation_id and sources

SSE events sent to browser:
  {"type": "step",  "content": "Analyzing question..."}         ← reasoning mode only
  {"type": "token", "content": "Diabetes"}                      ← both modes
  {"type": "done",  "content": "", "conversation_id": "abc",
   "sources": [{"source": "diabetes_guide.txt", "score": 0.87}]}

Internal-only events (never forwarded to browser):
  {"type": "_sources", "content": [...]}  ← from reasoning_service, intercepted here

Phase 4 additions:
  - Reasoning mode: routes to reasoning_service.reason_stream() instead of llm_service
  - Fallback: if mode="reasoning" but GROQ_API_KEY is not set, falls back to normal
  - step events: forwarded to browser so UI can show live reasoning progress
"""

import base64
import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.config import settings
from app.models.database import Attachment, Conversation, Message, get_db
from app.models.schemas import ChatRequest
from app.prompts.medical import build_system_prompt
from app.services import rag_service, reasoning_service
from app.services.llm_service import llm_service

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat")
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Main chat endpoint. Streams back the LLM response as SSE events.

    Two modes:
      normal    — RAG + Mistral 7B directly (~10-20s)
      reasoning — Groq plans → RAG + Mistral researches → Groq synthesizes (~30-45s)
    """

    async def event_generator():

        # ── Step 1: Create or load conversation ──────────────────────────
        conversation_id = request.conversation_id

        if not conversation_id:
            conversation = Conversation(
                title=request.message[:50],
                user_id="anonymous",
            )
            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)
            conversation_id = conversation.id

        # ── Step 2: Save user message ─────────────────────────────────────
        user_message = Message(
            conversation_id=conversation_id,
            role="user",
            content=request.message,
        )
        db.add(user_message)
        await db.commit()

        # ── Step 3: Process file attachments (Phase 2) ───────────────────
        attachment_context = ""
        image_descriptions = []

        if request.attachments:
            result = await db.execute(
                select(Attachment).where(Attachment.id.in_(request.attachments))
            )
            attachments = result.scalars().all()

            for attachment in attachments:
                attachment.message_id = user_message.id

                if attachment.extracted_text:
                    attachment_context += (
                        f"\n\n--- Attached file: {attachment.filename} ---\n"
                        f"{attachment.extracted_text}\n"
                        f"--- End of {attachment.filename} ---\n"
                    )

                if attachment.file_type == "image":
                    try:
                        import ollama as ollama_client

                        with open(attachment.file_path, "rb") as img_file:
                            img_b64 = base64.b64encode(img_file.read()).decode()

                        vision_response = ollama_client.chat(
                            model="moondream",
                            messages=[{
                                "role": "user",
                                "content": "Describe this image in detail. What do you see?",
                                "images": [img_b64],
                            }],
                        )
                        description = vision_response["message"]["content"]
                        image_descriptions.append(
                            f"\n[Visual analysis of {attachment.filename}]: {description}"
                        )
                    except Exception as e:
                        image_descriptions.append(
                            f"\n[Could not analyze image {attachment.filename}: {e}]"
                        )

            await db.commit()

        # ── Step 4: Route to normal or reasoning mode ─────────────────────
        #
        # NORMAL MODE:
        #   RAG search → build_system_prompt → llm_service.chat_stream()
        #
        # REASONING MODE:
        #   reasoning_service.reason_stream() handles everything internally:
        #   planning (Groq) → research (RAG + Mistral) → synthesis (Groq stream)
        #
        # FALLBACK:
        #   If reasoning is requested but GROQ_API_KEY is not set in .env,
        #   we fall back to normal mode with a notice step event.
        #   The app never crashes — Groq is optional.

        use_reasoning = (
            request.mode == "reasoning"
            and bool(settings.groq_api_key)
        )

        full_response = ""
        sources: list[dict] = []

        if use_reasoning:
            # ── REASONING MODE ─────────────────────────────────────────────
            print(f"[Chat] Reasoning mode for: {request.message[:60]}...")

            async for event_json in reasoning_service.reason_stream(
                request.message,
                attachment_context=attachment_context,
                image_descriptions=image_descriptions,
            ):
                data = json.loads(event_json)

                if data["type"] == reasoning_service.SOURCES_SENTINEL:
                    # Intercept sources — add to done event, don't send to browser
                    sources = data["content"]

                elif data["type"] == "token":
                    # Accumulate full response for saving to DB
                    full_response += data["content"]
                    yield event_json

                else:
                    # step events — forward directly to browser
                    yield event_json

        else:
            # ── NORMAL MODE ────────────────────────────────────────────────
            if request.mode == "reasoning" and not settings.groq_api_key:
                # Inform user why we're falling back
                yield json.dumps({
                    "type": "step",
                    "content": "Groq API key not configured — using standard mode. Add GROQ_API_KEY to backend/.env to enable reasoning mode.",
                })

            # RAG retrieval
            rag_sources = rag_service.search(request.message, n_results=3)

            if rag_sources:
                print(f"[RAG] {len(rag_sources)} chunk(s) found for: {request.message[:60]}...")
            else:
                print("[RAG] No relevant chunks found (knowledge base may be empty).")

            # Build system prompt with RAG context + attachments
            system_prompt = build_system_prompt(
                rag_sources=rag_sources,
                attachment_context=attachment_context,
                image_descriptions=image_descriptions,
            )

            messages = [{"role": "user", "content": request.message}]

            async for token in llm_service.chat_stream(messages, system_prompt):
                full_response += token
                yield json.dumps({"type": "token", "content": token})

            sources = [
                {"source": s["source"], "score": s["score"]}
                for s in rag_sources
            ]

        # ── Step 5: Save assistant response to DB ─────────────────────────
        assistant_message = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=full_response,
        )
        db.add(assistant_message)
        await db.commit()

        # ── Step 6: Send done event with sources ──────────────────────────
        yield json.dumps({
            "type": "done",
            "content": "",
            "conversation_id": conversation_id,
            "sources": sources,
        })

    return EventSourceResponse(event_generator())
