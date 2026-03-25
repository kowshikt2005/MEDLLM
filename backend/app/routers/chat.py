"""
Chat router — the core endpoint that connects the frontend to the LLM.

How streaming works end-to-end:
  1. Browser sends POST /api/chat with {"message": "What is diabetes?"}
  2. This endpoint creates an SSE (Server-Sent Events) response
  3. For each token Ollama generates, we send an SSE event to the browser
  4. The browser's ReadableStream reads each event and appends it to the UI
  5. When done, we send a final "done" event

SSE event format (what the browser receives):
  data: {"type": "token", "content": "Diabetes"}
  data: {"type": "token", "content": " is"}
  data: {"type": "token", "content": " a"}
  ...
  data: {"type": "done", "content": "", "conversation_id": "abc-123"}
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
from app.services.llm_service import llm_service

router = APIRouter(prefix="/api", tags=["chat"])

# Default system prompt for Phase 1 (will be enhanced with RAG in Phase 3)
SYSTEM_PROMPT = """You are MedLLM, a helpful and knowledgeable medical AI assistant.

Guidelines:
- Provide accurate, evidence-based medical information
- Use clear, understandable language while maintaining medical accuracy
- Always remind users to consult healthcare professionals for medical decisions
- If you're unsure about something, say so rather than guessing
- Structure your responses with headings and bullet points when appropriate

IMPORTANT: You are an AI assistant, not a doctor. Always recommend professional medical consultation for diagnosis and treatment decisions."""


@router.post("/chat")
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Main chat endpoint. Accepts a message and streams back the LLM response.

    This returns an EventSourceResponse — a special HTTP response that keeps
    the connection open and sends data as it becomes available (SSE).

    The browser doesn't get one big response. Instead, it receives a stream
    of small JSON events, each containing one token.
    """

    async def event_generator():
        """
        This inner function is the actual generator that produces SSE events.
        It runs asynchronously — FastAPI calls it and streams the results.
        """
        # ── Step 1: Create or load conversation ──────────
        conversation_id = request.conversation_id

        if not conversation_id:
            # New conversation — create one
            # Note: user_id is required by the database schema.
            # For now, we use a placeholder. In Phase 6, we'll wire this
            # to the authenticated user via get_current_user dependency.
            conversation = Conversation(
                title=request.message[:50],
                user_id="anonymous",
            )
            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)
            conversation_id = conversation.id

        # ── Step 2: Save the user's message to database ──
        user_message = Message(
            conversation_id=conversation_id,
            role="user",
            content=request.message,
        )
        db.add(user_message)
        await db.commit()

        # ── Step 3: Process attachments ──────────────────
        # If the user included file attachments, look them up, link them
        # to this message, and build context from their extracted text.
        attachment_context = ""
        image_descriptions = []

        if request.attachments:
            # Fetch all referenced attachments from the database
            result = await db.execute(
                select(Attachment).where(Attachment.id.in_(request.attachments))
            )
            attachments = result.scalars().all()

            for attachment in attachments:
                # Link attachment to this message (was null until now)
                attachment.message_id = user_message.id

                # Build context from extracted text
                if attachment.extracted_text:
                    attachment_context += (
                        f"\n\n--- Attached file: {attachment.filename} ---\n"
                        f"{attachment.extracted_text}\n"
                        f"--- End of {attachment.filename} ---\n"
                    )

                # For images, also get a vision description from moondream
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

        # ── Step 4: Build conversation history for the LLM ──
        # The LLM needs to see previous messages to maintain context.
        # We format them as [{"role": "user", "content": "..."}, ...]
        messages = [{"role": "user", "content": request.message}]

        # TODO (Phase 3): Add RAG context here
        # TODO (Phase 4): Handle reasoning mode here

        # Build system prompt with attachment context
        system_prompt = SYSTEM_PROMPT
        if attachment_context or image_descriptions:
            system_prompt += "\n\nThe user has attached the following files. Use this content to answer their question:"
            system_prompt += attachment_context
            for desc in image_descriptions:
                system_prompt += desc

        # ── Step 5: Stream tokens from Ollama ────────────
        full_response = ""

        async for token in llm_service.chat_stream(messages, system_prompt):
            full_response += token

            # Send each token as an SSE event
            yield json.dumps({"type": "token", "content": token})

        # ── Step 6: Save assistant's full response ───────
        assistant_message = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=full_response,
        )
        db.add(assistant_message)
        await db.commit()

        # ── Step 7: Send "done" event ────────────────────
        yield json.dumps({
            "type": "done",
            "content": "",
            "conversation_id": conversation_id,
        })

    # Return an SSE response that streams the generator's output
    return EventSourceResponse(event_generator())
