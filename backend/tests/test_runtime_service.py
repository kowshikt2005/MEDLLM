from app.config import Settings
from app.services.runtime_service import inspect_runtime


class FakeClient:
    def __init__(self, response):
        self.response = response

    def list(self):
        return self.response


def test_inspect_runtime_reports_configured_model_and_baseline_match():
    status = inspect_runtime(
        FakeClient({"models": [{"name": "mistral:latest", "digest": "6577803aa9a0"}]}),
        selected_model="mistral:latest",
        baseline_identifier="6577803aa9a0",
    )

    assert status.ollama_available is True
    assert status.selected_model_available is True
    assert status.selected_model_matches_baseline is True
    assert status.models[0].name == "mistral:latest"


def test_inspect_runtime_reports_missing_selected_model():
    status = inspect_runtime(
        FakeClient({"models": [{"name": "mistral:latest", "digest": "6577803aa9a0"}]}),
        selected_model="qwen:missing",
        baseline_identifier="6577803aa9a0",
    )

    assert status.ollama_available is True
    assert status.selected_model_available is False
    assert "not installed" in status.message


def test_inspect_runtime_reports_connection_failure():
    class OfflineClient:
        def list(self):
            raise ConnectionError("offline")

    status = inspect_runtime(
        OfflineClient(),
        selected_model="mistral:latest",
        baseline_identifier=None,
    )

    assert status.ollama_available is False
    assert status.selected_model_available is False
    assert "Ollama" in status.message

def test_settings_use_the_mistral_baseline_by_default(monkeypatch):
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    settings = Settings(_env_file=None)

    assert settings.ollama_model == "mistral:latest"
    assert settings.ollama_baseline_identifier == "6577803aa9a0"

def test_inspect_runtime_hides_the_retired_medllama_model():
    status = inspect_runtime(
        FakeClient({
            "models": [
                {"name": "medllama:latest", "digest": "64b28cb3259a"},
                {"name": "mistral:latest", "digest": "6577803aa9a0"},
            ]
        }),
        selected_model="medllama:latest",
        baseline_identifier="6577803aa9a0",
    )

    assert status.selected_model_available is False
    assert [model.name for model in status.models] == ["mistral:latest"]
    assert "retired" in status.message