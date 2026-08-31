"""Small, testable helpers for inspecting the local Ollama runtime."""

from dataclasses import dataclass
from typing import Any

import ollama

from app.config import settings


RETIRED_OLLAMA_MODELS = frozenset({'medllama:latest'})


@dataclass(frozen=True)
class RuntimeModel:
    name: str
    identifier: str | None


@dataclass(frozen=True)
class RuntimeStatus:
    ollama_available: bool
    selected_model: str
    selected_model_available: bool
    selected_model_matches_baseline: bool | None
    models: list[RuntimeModel]
    message: str | None


def _value(item: Any, *names: str) -> Any:
    for name in names:
        if isinstance(item, dict) and name in item:
            return item[name]
        value = getattr(item, name, None)
        if value is not None:
            return value
    return None


def inspect_runtime(
    client: object,
    selected_model: str,
    baseline_identifier: str | None,
) -> RuntimeStatus:
    """Return a normalized runtime status without raising client errors."""
    try:
        response = client.list()
    except Exception:
        return RuntimeStatus(
            ollama_available=False,
            selected_model=selected_model,
            selected_model_available=False,
            selected_model_matches_baseline=None,
            models=[],
            message="Ollama is unavailable. Start Ollama and retry.",
        )

    raw_models = _value(response, "models") or []
    models = [
        RuntimeModel(
            name=str(_value(raw_model, "name", "model") or ""),
            identifier=(
                str(_value(raw_model, "digest", "id"))
                if _value(raw_model, "digest", "id")
                else None
            ),
        )
        for raw_model in raw_models
    ]
    models = [
        model for model in models
        if model.name.lower() not in RETIRED_OLLAMA_MODELS
    ]

    if selected_model.lower() in RETIRED_OLLAMA_MODELS:
        return RuntimeStatus(
            ollama_available=True,
            selected_model=selected_model,
            selected_model_available=False,
            selected_model_matches_baseline=None,
            models=models,
            message=(
                f"Model '{selected_model}' is retired for this project and cannot be selected. "
                "Choose another installed model."
            ),
        )

    selected = next((model for model in models if model.name == selected_model), None)

    if selected is None:
        return RuntimeStatus(
            ollama_available=True,
            selected_model=selected_model,
            selected_model_available=False,
            selected_model_matches_baseline=None,
            models=models,
            message=(
                f"Ollama is running, but model '{selected_model}' is not installed. "
                "Choose an installed model or pull it before chatting."
            ),
        )

    matches_baseline = (
        selected.identifier == baseline_identifier
        if baseline_identifier
        else None
    )
    return RuntimeStatus(
        ollama_available=True,
        selected_model=selected_model,
        selected_model_available=True,
        selected_model_matches_baseline=matches_baseline,
        models=models,
        message=None,
    )

def inspect_configured_runtime() -> RuntimeStatus:
    """Inspect the configured local model without raising connection errors."""
    client = ollama.Client(host=settings.ollama_host)
    return inspect_runtime(
        client,
        selected_model=settings.ollama_model,
        baseline_identifier=settings.ollama_baseline_identifier,
    )