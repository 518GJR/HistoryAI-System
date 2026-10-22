import json

import numpy as np
import pytest

from app.services import rag_service, vector_service


class FakeTokenizer:
    def __call__(self, text, add_special_tokens=True, truncation=False):
        return {"input_ids": list(range(max(1, len(text) // 2)))}


class FakeEmbeddingModel:
    tokenizer = FakeTokenizer()
    max_seq_length = 512

    def encode(self, texts, **kwargs):
        rows = []
        for text in texts:
            if "灰烬、烧石和烧骨" in text or (
                text.startswith(vector_service.QUERY_PREFIX) and "火" in text
            ):
                rows.append([1.0, 0.0, 0.0])
            elif "北京人" in text:
                rows.append([0.8, 0.6, 0.0])
            else:
                rows.append([0.0, 0.0, 1.0])
        values = np.asarray(rows, dtype=np.float32)
        values /= np.linalg.norm(values, axis=1, keepdims=True)
        return values


def test_source_documents_deduplicate_and_preserve_associations(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_MODE", "textbook")
    items = rag_service.load_textbook_knowledge_from_json()

    documents = vector_service.build_source_documents(items)

    assert len(documents) == 35
    assert len({document["source_id"] for document in documents}) == 35
    shared = next(d for d in documents if d["source_id"] == "H7A-P004-A")
    assert len(shared["knowledge_ids"]) == 4
    assert shared["excerpt"].startswith("化石是研究古人类历史")
    assert shared["textbook_pages"] == "4"
    assert shared["pdf_pages"] == "9"
    assert "教材原文：" in shared["embedding_text"]


def test_source_document_conflict_fails_explicitly(monkeypatch):
    items = rag_service.load_textbook_knowledge_from_json()
    conflicting = dict(items[0])
    conflicting["knowledge_id"] = "CONFLICT"
    conflicting["source_refs"] = [dict(items[0]["source_refs"][0])]
    conflicting["source_refs"][0]["excerpt"] = "不一致原文"

    with pytest.raises(vector_service.VectorIndexError, match="Conflicting source"):
        vector_service.build_source_documents([items[0], conflicting])


def test_mock_index_build_load_and_vector_ranking(monkeypatch, tmp_path):
    index_file = tmp_path / "index.npz"
    monkeypatch.setenv("KNOWLEDGE_MODE", "textbook")
    monkeypatch.setenv("RETRIEVAL_MODE", "vector")
    monkeypatch.setenv("VECTOR_INDEX_PATH", str(index_file))
    monkeypatch.setattr(vector_service, "get_embedding_model", lambda: FakeEmbeddingModel())

    metadata = vector_service.build_vector_index(index_file, FakeEmbeddingModel())
    results = rag_service.retrieve_history_knowledge("北京人用火的意义是什么？")

    assert metadata["vector_count"] == 35
    assert metadata["vector_dimension"] == 3
    assert metadata["maximum_document_tokens"] <= metadata["model_max_tokens"]
    assert results[0]["source_refs"][0]["source_id"] == "H7A-P006-B"
    assert results[0]["retrieval_mode"] == "vector"
    assert results[0]["retrieval_unit"] == "source_excerpt"
    assert len(results) == 3


def test_index_data_hash_mismatch_requires_rebuild(monkeypatch, tmp_path):
    index_file = tmp_path / "index.npz"
    monkeypatch.setenv("VECTOR_INDEX_PATH", str(index_file))
    vector_service.build_vector_index(index_file, FakeEmbeddingModel())
    changed_data = tmp_path / "changed.json"
    changed_data.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(vector_service, "TEXTBOOK_DATA_FILE", changed_data)

    with pytest.raises(vector_service.VectorIndexError, match="rebuild it"):
        vector_service.load_vector_index(index_file)


def test_corrupt_index_fails_without_keyword_fallback(monkeypatch, tmp_path):
    corrupt = tmp_path / "index.npz"
    corrupt.write_text("not npz", encoding="utf-8")
    monkeypatch.setenv("KNOWLEDGE_MODE", "textbook")
    monkeypatch.setenv("RETRIEVAL_MODE", "vector")
    monkeypatch.setenv("VECTOR_INDEX_PATH", str(corrupt))

    with pytest.raises(rag_service.KnowledgeDataError, match="corrupt"):
        rag_service.retrieve_history_knowledge("北京人")


def test_missing_index_fails_without_keyword_fallback(monkeypatch, tmp_path):
    monkeypatch.setenv("KNOWLEDGE_MODE", "textbook")
    monkeypatch.setenv("RETRIEVAL_MODE", "vector")
    monkeypatch.setenv("VECTOR_INDEX_PATH", str(tmp_path / "missing.npz"))

    with pytest.raises(rag_service.KnowledgeDataError, match="not found"):
        rag_service.retrieve_history_knowledge("北京人")


def test_model_load_failure_is_exposed_without_fallback(monkeypatch, tmp_path):
    index_file = tmp_path / "index.npz"
    vector_service.build_vector_index(index_file, FakeEmbeddingModel())
    monkeypatch.setenv("KNOWLEDGE_MODE", "textbook")
    monkeypatch.setenv("RETRIEVAL_MODE", "vector")
    monkeypatch.setenv("VECTOR_INDEX_PATH", str(index_file))

    def fail_model_load():
        raise vector_service.VectorIndexError("mock model load failure")

    monkeypatch.setattr(vector_service, "get_embedding_model", fail_model_load)
    with pytest.raises(rag_service.KnowledgeDataError, match="model load failure"):
        rag_service.retrieve_history_knowledge("北京人")


def test_keyword_mode_does_not_touch_vector_runtime(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_MODE", "textbook")
    monkeypatch.setenv("RETRIEVAL_MODE", "keyword")

    def fail_if_called(*args, **kwargs):
        raise AssertionError("keyword mode must not use vector runtime")

    monkeypatch.setattr(vector_service, "retrieve_textbook_vectors", fail_if_called)
    results = rag_service.retrieve_history_knowledge("北京人用火有什么作用？")

    assert results
    assert all(result["retrieval_mode"] == "keyword" for result in results)


def test_vector_mode_rejects_demo_knowledge(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_MODE", "demo")
    monkeypatch.setenv("RETRIEVAL_MODE", "vector")

    with pytest.raises(rag_service.KnowledgeDataError, match="requires"):
        rag_service.retrieve_history_knowledge("秦始皇")


def test_index_metadata_json_contains_no_summary_or_certainty_in_embedding_text():
    items = rag_service.load_textbook_knowledge_from_json()
    documents = vector_service.build_source_documents(items)
    raw_payload = json.loads(vector_service.TEXTBOOK_DATA_FILE.read_text(encoding="utf-8"))
    excerpts = {source["source_id"]: source["excerpt"] for source in raw_payload["sources"]}

    assert all(document["excerpt"] == excerpts[document["source_id"]] for document in documents)
    assert all("certainty" not in document["embedding_text"] for document in documents)
