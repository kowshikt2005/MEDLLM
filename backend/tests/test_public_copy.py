from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_public_copy_does_not_make_unsupported_medical_or_currentness_claims():
    homepage = (ROOT / "frontend" / "src" / "components" / "HomePage.jsx").read_text(encoding="utf-8")
    chat_view = (ROOT / "frontend" / "src" / "components" / "ChatView.jsx").read_text(encoding="utf-8")
    main = (ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")

    for unsupported_claim in (
        "99.8% accuracy",
        "updated daily",
        "Clinically Validated",
        "rare condition",
        "Medical Diagnostics",
    ):
        assert unsupported_claim not in homepage
    assert "medical AI assistant" not in chat_view
    assert "Medical AI Assistant" not in main
