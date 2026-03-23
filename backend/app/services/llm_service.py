"""
LLM Service — communicates with Ollama for local model inference.

This service wraps the Ollama Python client and provides:
  1. chat_stream() — Send a message, get tokens back one at a time (for SSE)
  2. chat()       — Send a message, get the full response at once (for reasoning mode)

How Ollama works under the hood:
  - Ollama runs as a background process on your machine (localhost:11434)
  - It loads the model (e.g., Mistral-7B) into RAM/VRAM
  - We send it a list of messages (like a conversation transcript)
  - It predicts the next tokens one at a time
  - With stream=True, each token is sent back immediately as it's generated
    instead of waiting for the full response
"""

from collections.abc import AsyncGenerator

import ollama

from app.config import settings


class LLMService:
    def __init__(self):
        """
        Initialize the Ollama client.
        The host comes from config.py (default: http://localhost:11434).
        """
        self.client = ollama.Client(host=settings.ollama_host)
        self.model = settings.ollama_model

    async def chat_stream(
        self,
        messages: list[dict],
        system_prompt: str = "",
    ) -> AsyncGenerator[str, None]:
        """
        Send messages to Ollama and yield response tokens one at a time.

        This is an "async generator" — it produces values over time rather
        than returning one value. The chat endpoint reads these tokens and
        sends each one to the browser as an SSE event.

        Parameters:
            messages: List of {"role": "user"|"assistant", "content": "..."}
            system_prompt: Instructions for the model (e.g., "You are a medical AI")

        Yields:
            str: One token (word or word fragment) at a time

        Example:
            async for token in llm.chat_stream(messages, system_prompt):
                print(token, end="")  # prints: "Diabetes " "is " "a " "chronic " ...
        """
        # Build the full message list: system prompt first, then conversation
        full_messages = []

        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})

        full_messages.extend(messages)

        try:
            # stream=True tells Ollama to send tokens as they're generated
            stream = self.client.chat(
                model=self.model,
                messages=full_messages,
                stream=True,
            )

            # Each chunk from the stream contains one token
            for chunk in stream:
                token = chunk["message"]["content"]
                if token:
                    yield token

        except ollama.ResponseError as e:
            # Model not found or Ollama returned an error
            yield f"\n\n[Error: Ollama returned an error — {e.error}]"
        except Exception as e:
            # Ollama not running or network issue
            yield f"\n\n[Error: Could not connect to Ollama at {settings.ollama_host}. Is Ollama running? Error: {str(e)}]"

    async def chat(
        self,
        messages: list[dict],
        system_prompt: str = "",
    ) -> str:
        """
        Send messages to Ollama and get the FULL response at once.
        Used in reasoning mode where we need the complete response
        before passing it to the next step.

        Returns:
            str: The complete response text
        """
        full_messages = []

        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})

        full_messages.extend(messages)

        try:
            response = self.client.chat(
                model=self.model,
                messages=full_messages,
                stream=False,
            )
            return response["message"]["content"]

        except ollama.ResponseError as e:
            return f"[Error: Ollama returned an error — {e.error}]"
        except Exception as e:
            return f"[Error: Could not connect to Ollama at {settings.ollama_host}. Is Ollama running? Error: {str(e)}]"

    def is_available(self) -> bool:
        """
        Check if Ollama is running and the model is loaded.
        Useful for health checks and showing status in the UI.
        """
        try:
            self.client.list()
            return True
        except Exception:
            return False


# Single global instance
llm_service = LLMService()
