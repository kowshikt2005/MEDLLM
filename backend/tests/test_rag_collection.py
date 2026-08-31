from pathlib import Path


def test_delete_documents_by_corpus_filters_to_the_named_corpus():
    source = (
        Path(__file__).resolve().parents[1] / "app" / "services" / "rag_service.py"
    ).read_text(encoding="utf-8")

    assert "def delete_documents_by_corpus(corpus: str) -> None:" in source
    assert 'collection.delete(where={"corpus": corpus})' in source