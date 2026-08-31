from app.prompts.medical import BASE_SYSTEM_PROMPT, RAG_CONTEXT_TEMPLATE, build_system_prompt


def test_normal_prompt_requires_retrieved_evidence_or_abstention():
    prompt = build_system_prompt(
        rag_sources=[
            {
                "source": "Diabetes Basics",
                "score": 0.9,
                "text": "A retrieved source excerpt.",
            }
        ]
    )

    assert "Do not answer from general knowledge" in BASE_SYSTEM_PROMPT
    assert "Do not answer from general knowledge" in RAG_CONTEXT_TEMPLATE
    assert "If no retrieved source supports the question, abstain" in prompt

def test_normal_chat_abstains_before_generation_when_retrieval_is_empty():
    from pathlib import Path

    chat_source = (
        Path(__file__).resolve().parents[1] / "app" / "routers" / "chat.py"
    ).read_text(encoding="utf-8")

    assert "NO_RETRIEVED_EVIDENCE_MESSAGE" in chat_source
    assert "normal_rag_sources = rag_service.search(request.message, n_results=3)" in chat_source
    assert "if not normal_rag_sources:" in chat_source
    assert '"type": "token", "content": NO_RETRIEVED_EVIDENCE_MESSAGE' in chat_source

def test_retrieval_exposes_source_provenance_for_citations():
    from pathlib import Path

    rag_source = (
        Path(__file__).resolve().parents[1] / "app" / "services" / "rag_service.py"
    ).read_text(encoding="utf-8")

    assert '"source_id": meta.get("source_id")' in rag_source
    assert '"url": meta.get("url")' in rag_source
    assert '"publisher": meta.get("publisher")' in rag_source
    assert '"corpus": meta.get("corpus")' in rag_source