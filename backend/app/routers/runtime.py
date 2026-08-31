"""Runtime status endpoint for local Ollama model discovery."""

from fastapi import APIRouter

from app.services.runtime_service import RuntimeStatus, inspect_configured_runtime

router = APIRouter(prefix="/api", tags=["runtime"])


@router.get("/runtime")
def get_runtime() -> RuntimeStatus:
    return inspect_configured_runtime()
