import pytest

from app.services.runtime_service import RuntimeStatus


def _ready_status() -> RuntimeStatus:
    return RuntimeStatus(
        ollama_available=True,
        selected_model="mistral:latest",
        selected_model_available=True,
        selected_model_matches_baseline=True,
        models=[],
        message=None,
    )


def test_runtime_route_returns_the_current_status(monkeypatch):
    from app.routers import runtime

    expected = _ready_status()
    monkeypatch.setattr(runtime, "inspect_configured_runtime", lambda: expected)

    assert runtime.get_runtime() == expected


def test_main_registers_runtime_route():
    from pathlib import Path

    main_source = (
        Path(__file__).resolve().parents[1] / "app" / "main.py"
    ).read_text(encoding="utf-8")

    assert "runtime" in main_source and "from app.routers import" in main_source
    assert "app.include_router(runtime.router)" in main_source

@pytest.mark.asyncio
async def test_chat_stream_uses_the_requested_model():
    from app.services.llm_service import LLMService

    class FakeClient:
        def __init__(self):
            self.model = None

        def chat(self, *, model, messages, stream, options=None):
            self.model = model
            return iter([{"message": {"content": "grounded reply"}}])

    service = LLMService.__new__(LLMService)
    service.client = FakeClient()
    service.model = "mistral:latest"

    tokens = [
        token
        async for token in service.chat_stream(
            [{"role": "user", "content": "question"}],
            model="custom-local-model",
        )
    ]

    assert tokens == ["grounded reply"]
    assert service.client.model == "custom-local-model"

def test_chat_request_preserves_the_selected_model():
    from app.models.schemas import ChatRequest

    request = ChatRequest(message="What is diabetes?", model="custom-local-model")

    assert request.model == "custom-local-model"

def test_normal_chat_validates_and_uses_the_selected_model():
    from pathlib import Path

    chat_source = (
        Path(__file__).resolve().parents[1] / "app" / "routers" / "chat.py"
    ).read_text(encoding="utf-8")

    assert "inspect_runtime(" in chat_source
    assert '"type": "error"' in chat_source
    assert "model=selected_model" in chat_source