import json
from pathlib import Path

from app.config import Settings


def test_model_provenance_matches_the_configured_mistral_baseline(monkeypatch):
    provenance = json.loads(
        (Path(__file__).resolve().parents[1] / "model-provenance.json").read_text(encoding="utf-8")
    )
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    settings = Settings(_env_file=None)

    baseline = provenance["baseline"]
    assert baseline["ollama_model"] == settings.ollama_model == "mistral:latest"
    assert baseline["ollama_list_identifier"] == settings.ollama_baseline_identifier
    assert provenance["quality_claim"] == "No medical reliability or accuracy claim is made for this model."
    assert "medllama:latest" in provenance["retired_models"]
