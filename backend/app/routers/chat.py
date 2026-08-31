import base64
import json
import time
from uuid import uuid4

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.config import settings
from app.models.database import Attachment, Conversation, HealthProfile, Message, User, get_db
from app.models.schemas import ChatRequest
from app.prompts.medical import NO_RETRIEVED_EVIDENCE_MESSAGE, build_system_prompt
from app.routers.auth import get_current_user
from app.services import rag_service, reasoning_service
from app.services.cancellation import (
    clear_cancellation,
    is_cancelled,
    mark_cancelled,
    register_active,
)
from app.services.llm_service import llm_service
from app.services.runtime_service import inspect_runtime

router = APIRouter(prefix="/api", tags=["chat"])


def _build_grounded_query(user_query: str) -> str:
    """Keep the user question intact while reiterating the evidence boundary."""
    return (
        f"Question: {user_query}\n\n"
        "Answer only from the retrieved excerpts. If they do not support the question, abstain."
    )


# Emergency detection keywords — deterministic pre-check before any LLM call
EMERGENCY_KEYWORDS = [
    "chest pain", "can't breathe", "difficulty breathing", "unconscious",
    "severe bleeding", "suicide", "overdose", "seizure", "stroke",
    "heart attack", "cardiac arrest", "anaphylaxis", "allergic reaction",
    "poisoning", "burns", "fracture", "head injury", "drowning"
]


def _is_emergency(query: str) -> bool:
    q = (query or "").lower()
    return any(k in q for k in EMERGENCY_KEYWORDS)


def _dedupe_sources(sources: list[dict]) -> list[dict]:
    """Merge duplicate source labels and keep the highest confidence score."""
    merged: dict[str, float] = {}
    for src in sources:
        label = str(src.get("source") or "Unknown")
        score = float(src.get("score") or 0.0)
        merged[label] = max(merged.get(label, 0.0), score)
    return [
        {"source": label, "score": round(score, 3)}
        for label, score in merged.items()
    ]


@router.post("/chat")
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Main chat endpoint. Streams back the LLM response as SSE events."""

    async def event_generator():
        req_id = uuid4().hex[:8]
        started_at = time.perf_counter()
        token_chunks = 0
        conversation_id: str | None = request.conversation_id
        full_response = ""
        sources: list[dict] = []

        print(
            f"[Chat:{req_id}] Incoming request | mode={request.mode} | "
            f"has_conversation={bool(request.conversation_id)} | attachments={len(request.attachments)}",
            flush=True,
        )

        # Send request id immediately so the frontend can cancel this stream.
        await register_active(req_id)
        yield json.dumps({"type": "init", "request_id": req_id})
        selected_model = request.model or settings.ollama_model
        normal_mode_required = not (request.mode == "reasoning" and bool(settings.groq_api_key))
        normal_rag_sources: list[dict] | None = None
        if normal_mode_required:
            runtime_status = inspect_runtime(
                llm_service.client,
                selected_model=selected_model,
                baseline_identifier=settings.ollama_baseline_identifier,
            )
            if not runtime_status.selected_model_available:
                yield json.dumps({"type": "error", "content": runtime_status.message or "The selected Ollama model is unavailable."})
                return
            yield json.dumps({"type": "step", "content": "Checking retrieved references..."})
            normal_rag_sources = rag_service.search(request.message, n_results=3)
            if not normal_rag_sources:
                yield json.dumps({"type": "token", "content": NO_RETRIEVED_EVIDENCE_MESSAGE})
                yield json.dumps({"type": "done", "content": "", "conversation_id": None, "request_id": req_id, "sources": []})
                return

        try:
            if not conversation_id:
                conversation = Conversation(
                    title=request.message[:50],
                    user_id=current_user.id,
                )
                db.add(conversation)
                await db.commit()
                await db.refresh(conversation)
                conversation_id = conversation.id
            else:
                convo_result = await db.execute(
                    select(Conversation).where(
                        Conversation.id == conversation_id,
                        Conversation.user_id == current_user.id,
                    )
                )
                existing_conversation = convo_result.scalar_one_or_none()
                if existing_conversation is None:
                    yield json.dumps(
                        {
                            "type": "done",
                            "content": "Conversation not found for this patient.",
                            "conversation_id": None,
                            "request_id": req_id,
                            "sources": [],
                        }
                    )
                    return

            print(f"[Chat:{req_id}] Conversation: {conversation_id}", flush=True)

            user_message = Message(
                conversation_id=conversation_id,
                role="user",
                content=request.message,
            )
            db.add(user_message)
            await db.commit()

            attachment_context = ""
            patient_context = ""
            image_descriptions: list[str] = []

            if request.health_context:
                profile_result = await db.execute(
                    select(HealthProfile).where(HealthProfile.user_id == current_user.id)
                )
                profile = profile_result.scalar_one_or_none()
                if profile:
                    patient_context = (
                        f"Age: {profile.age or 'Unknown'}\n"
                        f"Gender: {profile.gender or 'Unknown'}\n"
                        f"Blood Type: {profile.blood_type or 'Unknown'}\n"
                        f"Allergies: {profile.allergies or 'None listed'}\n"
                        f"Current Medications: {profile.medications or 'None listed'}\n"
                        f"Chronic Conditions: {profile.conditions or 'None listed'}"
                    )

            if request.attachments:
                result = await db.execute(
                    select(Attachment).where(
                        Attachment.id.in_(request.attachments),
                        Attachment.user_id == current_user.id,
                    )
                )
                attachments = result.scalars().all()

                for attachment in attachments:
                    attachment.message_id = user_message.id

                    if attachment.file_type == "image" and not normal_mode_required:
                        try:
                            import ollama as ollama_client

                            with open(attachment.file_path, "rb") as img_file:
                                img_b64 = base64.b64encode(img_file.read()).decode()

                            vision_response = ollama_client.chat(
                                model="moondream",
                                messages=[
                                    {
                                        "role": "user",
                                        "content": "Describe this image in detail. What do you see?",
                                        "images": [img_b64],
                                    }
                                ],
                            )
                            description = vision_response["message"]["content"]
                            image_descriptions.append(
                                f"\n[Visual analysis of {attachment.filename}]: {description}"
                            )
                        except Exception as exc:
                            image_descriptions.append(
                                f"\n[Could not analyze image {attachment.filename}: {exc}]"
                            )

                await db.commit()

            print(
                f"[Chat:{req_id}] Image descriptions: {len(image_descriptions)}",
                flush=True,
            )

            use_reasoning = request.mode == "reasoning" and bool(settings.groq_api_key)

            if use_reasoning:
                print(
                    f"[Chat:{req_id}] Reasoning mode for: {request.message[:60]}...",
                    flush=True,
                )

                async for event_json in reasoning_service.reason_stream(
                    request.message,
                    attachment_context=attachment_context,
                    image_descriptions=image_descriptions,
                ):
                    if await is_cancelled(req_id):
                        print(
                            f"[Chat:{req_id}] Cancellation detected - stopping reasoning stream",
                            flush=True,
                        )
                        yield json.dumps(
                            {"type": "cancelled", "content": "Request cancelled by user."}
                        )
                        break

                    data = json.loads(event_json)

                    if data.get("type") == reasoning_service.SOURCES_SENTINEL:
                        sources = data.get("content") or []
                    elif data.get("type") == "token":
                        token = str(data.get("content") or "")
                        full_response += token
                        token_chunks += 1
                        if token_chunks % 40 == 0:
                            print(
                                f"[Chat:{req_id}] Streaming | token_chunks={token_chunks}",
                                flush=True,
                            )
                        yield event_json
                    else:
                        yield event_json
            else:
                yield json.dumps(
                    {
                        "type": "step",
                        "content": "Checking relevant medical references...",
                    }
                )

                if request.mode == "reasoning" and not settings.groq_api_key:
                    yield json.dumps(
                        {
                            "type": "step",
                            "content": "Groq API key not configured - using standard mode. Add GROQ_API_KEY to backend/.env to enable reasoning mode.",
                        }
                    )

                # Emergency pre-check: avoid any LLM call for potentially life-threatening queries
                if False and _is_emergency(request.message):
                    emergency_response = (
                        "🚨 EMERGENCY: This appears to be a potentially life-threatening medical situation. "
                        "Call emergency services (911 / 112 / 999) immediately. Do not wait for an AI response."
                    )
                    full_response = emergency_response
                    yield json.dumps({"type": "token", "content": emergency_response})
                    sources = []
                else:
                    rag_sources = normal_rag_sources or []

                    if rag_sources:
                        sources_brief = ", ".join([src["source"] for src in rag_sources])
                        print(
                            f"[Chat:{req_id}] RAG hits={len(rag_sources)} for: {request.message[:60]}... "
                            f"| sources=[{sources_brief}]",
                            flush=True,
                        )
                    else:
                        print(
                            f"[Chat:{req_id}] RAG hits=0 (knowledge base and attachments may be empty).",
                            flush=True,
                        )

                    yield json.dumps({"type": "step", "content": "Drafting your answer..."})

                    system_prompt = build_system_prompt(
                        rag_sources=rag_sources,
                        patient_context="",
                        attachment_context=attachment_context,
                        image_descriptions=[],
                    )

                    styled_query = _build_grounded_query(request.message)
                    messages = [{"role": "user", "content": styled_query}]

                    # Use Groq streaming for normal generation when API key is configured
                    if False and settings.groq_api_key:
                        try:
                            from groq import AsyncGroq

                            client = AsyncGroq(api_key=settings.groq_api_key)
                            full_messages = []
                            if system_prompt:
                                full_messages.append({"role": "system", "content": system_prompt})
                            full_messages.extend(messages)

                            async with client.chat.completions.stream(
                                model=settings.groq_model,
                                messages=full_messages,
                                temperature=settings.llm_temperature,
                                max_tokens=2048,
                            ) as stream:
                                async for chunk in stream:
                                    token = chunk.choices[0].delta.content or ""
                                    if await is_cancelled(req_id):
                                        print(
                                            f"[Chat:{req_id}] Cancellation detected - stopping Groq stream",
                                            flush=True,
                                        )
                                        yield json.dumps({"type": "cancelled", "content": "Request cancelled by user."})
                                        break

                                    if token:
                                        full_response += token
                                        token_chunks += 1
                                        if token_chunks % 40 == 0:
                                            print(f"[Chat:{req_id}] Streaming | token_chunks={token_chunks}", flush=True)
                                        yield json.dumps({"type": "token", "content": token})

                        except Exception as e:
                            print(f"[Chat:{req_id}] Groq stream failed: {e}; falling back to local Ollama.", flush=True)
                            # Fallback to local Ollama if Groq fails
                            async for token in llm_service.chat_stream(messages, system_prompt, model=selected_model):
                                if await is_cancelled(req_id):
                                    print(
                                        f"[Chat:{req_id}] Cancellation detected - stopping normal stream",
                                        flush=True,
                                    )
                                    yield json.dumps({"type": "cancelled", "content": "Request cancelled by user."})
                                    break

                                full_response += token
                                token_chunks += 1
                                if token_chunks % 40 == 0:
                                    print(f"[Chat:{req_id}] Streaming | token_chunks={token_chunks}", flush=True)
                                yield json.dumps({"type": "token", "content": token})
                    else:
                        # No Groq configured — use local Ollama
                        async for token in llm_service.chat_stream(messages, system_prompt, model=selected_model):
                            if await is_cancelled(req_id):
                                print(
                                    f"[Chat:{req_id}] Cancellation detected - stopping normal stream",
                                    flush=True,
                                )
                                yield json.dumps({"type": "cancelled", "content": "Request cancelled by user."})
                                break

                            full_response += token
                            token_chunks += 1
                            if token_chunks % 40 == 0:
                                print(f"[Chat:{req_id}] Streaming | token_chunks={token_chunks}", flush=True)
                            yield json.dumps({"type": "token", "content": token})

                    sources = [{"source": src["source"], "score": src["score"]} for src in rag_sources]
                    sources = _dedupe_sources(sources)

            was_cancelled = await is_cancelled(req_id)
            if not was_cancelled and full_response:
                assistant_message = Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_response,
                )
                db.add(assistant_message)
                await db.commit()

            elapsed = time.perf_counter() - started_at
            print(
                f"[Chat:{req_id}] {'CANCELLED' if was_cancelled else 'Completed'} | "
                f"seconds={elapsed:.2f} | token_chunks={token_chunks} | "
                f"response_chars={len(full_response)} | sources={len(sources)}",
                flush=True,
            )

            if was_cancelled:
                yield json.dumps(
                    {
                        "type": "done",
                        "content": "Request was cancelled.",
                        "conversation_id": conversation_id,
                        "request_id": req_id,
                        "sources": [],
                    }
                )
            else:
                yield json.dumps(
                    {
                        "type": "done",
                        "content": "",
                        "conversation_id": conversation_id,
                        "request_id": req_id,
                        "sources": _dedupe_sources(sources),
                    }
                )
        finally:
            await clear_cancellation(req_id)

    return EventSourceResponse(event_generator())


@router.post("/cancel")
async def cancel_request(request_id: str = Query(..., min_length=1)) -> dict:
    """Cancel an in-progress streaming request."""
    success = await mark_cancelled(request_id)
    return {"cancelled": success}
