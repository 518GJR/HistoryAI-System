"""Local dense retrieval over deduplicated textbook source excerpts."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[3]
TEXTBOOK_DATA_FILE = PROJECT_ROOT / "data" / "textbook_history_knowledge.json"
DEFAULT_INDEX_FILE = (
    PROJECT_ROOT / "data" / "vector_index" / "textbook_bge_small_zh_v1_5.npz"
)
DEFAULT_MODEL_ID = "BAAI/bge-small-zh-v1.5"
DEFAULT_MODEL_REVISION = "7999e1d3359715c523056ef9478215996d62a620"
QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："
INDEX_FORMAT_VERSION = "historyai-textbook-vector-v1"
PREPROCESSING = {
    "document_template": "书名：{book_title}\n第{lesson_number}课：{lesson_title}\n小标题：{section_title}\n教材原文：{excerpt}",
    "document_prefix": "",
    "query_prefix": QUERY_PREFIX,
    "whitespace": "strip-fields-preserve-excerpt",
    "chunking": "none-one-deduplicated-source-per-vector",
}


class VectorIndexError(RuntimeError):
    """The vector runtime or index is unavailable, invalid, or incompatible."""


_MODEL_CACHE: dict[tuple[str, str], Any] = {}
_MODEL_LOCK = threading.Lock()


def configured_model_id() -> str:
    return os.getenv("EMBEDDING_MODEL", DEFAULT_MODEL_ID).strip() or DEFAULT_MODEL_ID


def configured_model_revision() -> str:
    return (
        os.getenv("EMBEDDING_MODEL_REVISION", DEFAULT_MODEL_REVISION).strip()
        or DEFAULT_MODEL_REVISION
    )


def configured_index_file() -> Path:
    configured = os.getenv("VECTOR_INDEX_PATH", "").strip()
    if not configured:
        return DEFAULT_INDEX_FILE
    path = Path(configured)
    return path if path.is_absolute() else PROJECT_ROOT / path


def textbook_data_sha256(path: Path | None = None) -> str:
    source_path = path or TEXTBOOK_DATA_FILE
    try:
        return hashlib.sha256(source_path.read_bytes()).hexdigest()
    except OSError as exc:
        raise VectorIndexError(
            f"Cannot read textbook data for hashing: {source_path}"
        ) from exc


def _stable_unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def build_source_documents(knowledge_items: list[dict]) -> list[dict]:
    """Deduplicate by source_id and merge knowledge-point associations.

    Conflicting excerpt or source metadata is rejected rather than silently
    choosing one version.
    """
    documents: dict[str, dict] = {}
    for item in knowledge_items:
        knowledge_id = str(item.get("knowledge_id") or "").strip()
        if not knowledge_id:
            raise VectorIndexError("Knowledge point without knowledge_id")
        for reference in item.get("source_refs") or []:
            if not isinstance(reference, dict):
                raise VectorIndexError(f"Invalid source reference on {knowledge_id}")
            source_id = str(reference.get("source_id") or "").strip()
            excerpt = str(reference.get("excerpt") or "").strip()
            if not source_id or not excerpt:
                raise VectorIndexError(f"Incomplete source reference on {knowledge_id}")

            source_metadata = {
                "source_id": source_id,
                "parent_source_id": source_id,
                "fragment_id": source_id,
                "fragment_start": 0,
                "fragment_end": len(excerpt),
                "excerpt": excerpt,
                "book_id": str(item.get("book_id") or ""),
                "book_title": str(item.get("book_title") or ""),
                "unit_id": str(item.get("unit_id") or ""),
                "unit_title": str(item.get("unit_title") or ""),
                "lesson_id": str(item.get("lesson_id") or reference.get("lesson_id") or ""),
                "lesson_number": item.get("lesson_number"),
                "lesson_title": str(item.get("lesson_title") or ""),
                "section_id": str(reference.get("section_id") or ""),
                "section_title": str(item.get("section_title") or ""),
                "material_type": str(reference.get("material_type") or ""),
                "textbook_pages": str(reference.get("textbook_pages") or ""),
                "pdf_pages": str(reference.get("pdf_pages") or ""),
                "locator": str(reference.get("locator") or ""),
            }
            existing = documents.get(source_id)
            if existing is None:
                documents[source_id] = {
                    **source_metadata,
                    "knowledge_ids": [knowledge_id],
                    "knowledge_titles": [str(item.get("title") or "")],
                    "periods": [str(item.get("dynasty") or "")],
                    "qualifiers": list(item.get("qualifiers") or []),
                    "certainty_notes": [str(item.get("certainty") or "")],
                }
                continue

            for field, value in source_metadata.items():
                if existing[field] != value:
                    raise VectorIndexError(
                        f"Conflicting source metadata for {source_id}: {field}"
                    )
            existing["knowledge_ids"].append(knowledge_id)
            existing["knowledge_titles"].append(str(item.get("title") or ""))
            existing["periods"].append(str(item.get("dynasty") or ""))
            existing["qualifiers"].extend(item.get("qualifiers") or [])
            existing["certainty_notes"].append(str(item.get("certainty") or ""))

    result = []
    for document in documents.values():
        for field in (
            "knowledge_ids",
            "knowledge_titles",
            "periods",
            "qualifiers",
            "certainty_notes",
        ):
            document[field] = _stable_unique(document[field])
        document["embedding_text"] = PREPROCESSING["document_template"].format(
            **document
        )
        result.append(document)
    return result


def get_embedding_model():
    """Load one CPU model instance per configured id/revision per process."""
    key = (configured_model_id(), configured_model_revision())
    with _MODEL_LOCK:
        model = _MODEL_CACHE.get(key)
        if model is not None:
            return model
        try:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(
                key[0],
                revision=key[1],
                device="cpu",
                trust_remote_code=False,
            )
        except Exception as exc:
            raise VectorIndexError(
                f"Failed to load local embedding model {key[0]} at {key[1]}: {exc}"
            ) from exc
        _MODEL_CACHE[key] = model
        return model


def _validate_token_lengths(model, documents: list[dict]) -> dict:
    tokenizer = getattr(model, "tokenizer", None)
    max_length = int(getattr(model, "max_seq_length", 0) or 0)
    if tokenizer is None or max_length <= 0:
        raise VectorIndexError("Embedding model does not expose tokenizer/max_seq_length")
    maximum = 0
    for document in documents:
        token_ids = tokenizer(
            document["embedding_text"], add_special_tokens=True, truncation=False
        )["input_ids"]
        token_count = len(token_ids)
        maximum = max(maximum, token_count)
        if token_count > max_length:
            raise VectorIndexError(
                f"Source {document['source_id']} has {token_count} tokens, exceeding "
                f"model limit {max_length}; explicit chunking is required"
            )
    return {"model_max_tokens": max_length, "maximum_document_tokens": maximum}


def _validate_vectors(vectors: np.ndarray, expected_count: int) -> np.ndarray:
    values = np.asarray(vectors, dtype=np.float32)
    if values.ndim != 2 or values.shape[0] != expected_count or values.shape[1] <= 0:
        raise VectorIndexError(
            f"Invalid vector shape {values.shape}; expected {expected_count} rows"
        )
    if not np.isfinite(values).all():
        raise VectorIndexError("Vector index contains non-finite values")
    norms = np.linalg.norm(values, axis=1)
    if np.any(norms <= 0):
        raise VectorIndexError("Vector index contains zero-length vectors")
    if not np.allclose(norms, 1.0, atol=1e-4):
        raise VectorIndexError("Vector index rows are not L2 normalized")
    return values


def build_vector_index(index_file: Path | None = None, model=None) -> dict:
    """Build and atomically replace the local source-level vector index."""
    from app.services.rag_service import load_textbook_knowledge_from_json

    target = index_file or configured_index_file()
    documents = build_source_documents(load_textbook_knowledge_from_json())
    embedding_model = model or get_embedding_model()
    token_stats = _validate_token_lengths(embedding_model, documents)
    try:
        vectors = embedding_model.encode(
            [document["embedding_text"] for document in documents],
            batch_size=16,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
    except Exception as exc:
        raise VectorIndexError(f"Failed to encode textbook sources: {exc}") from exc
    vectors = _validate_vectors(vectors, len(documents))

    metadata = {
        "format_version": INDEX_FORMAT_VERSION,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "model_id": configured_model_id(),
        "model_revision": configured_model_revision(),
        "model_max_tokens": token_stats["model_max_tokens"],
        "maximum_document_tokens": token_stats["maximum_document_tokens"],
        "vector_dimension": int(vectors.shape[1]),
        "similarity": "cosine_via_dot_product",
        "normalization": "l2_unit_length",
        "preprocessing": PREPROCESSING,
        "textbook_data_sha256": textbook_data_sha256(),
        "vector_count": int(vectors.shape[0]),
        "documents": documents,
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{target.stem}.", suffix=".npz", dir=target.parent, delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
        np.savez_compressed(
            temporary_path,
            vectors=vectors,
            metadata=np.asarray(json.dumps(metadata, ensure_ascii=False)),
        )
        os.replace(temporary_path, target)
    except OSError as exc:
        raise VectorIndexError(f"Failed to atomically write vector index: {target}") from exc
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return metadata


def load_vector_index(index_file: Path | None = None) -> tuple[np.ndarray, dict]:
    """Load and fully validate an index against current data and configuration."""
    target = index_file or configured_index_file()
    if not target.exists():
        raise VectorIndexError(
            f"Vector index not found: {target}. Run the explicit build command first"
        )
    try:
        with np.load(target, allow_pickle=False) as payload:
            vectors = np.asarray(payload["vectors"], dtype=np.float32)
            metadata = json.loads(str(payload["metadata"].item()))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise VectorIndexError(f"Vector index is unreadable or corrupt: {target}") from exc
    if not isinstance(metadata, dict) or not isinstance(metadata.get("documents"), list):
        raise VectorIndexError("Vector index metadata is invalid")

    expected = {
        "format_version": INDEX_FORMAT_VERSION,
        "model_id": configured_model_id(),
        "model_revision": configured_model_revision(),
        "preprocessing": PREPROCESSING,
        "textbook_data_sha256": textbook_data_sha256(),
    }
    mismatches = [
        key for key, value in expected.items() if metadata.get(key) != value
    ]
    if mismatches:
        raise VectorIndexError(
            "Vector index does not match current configuration/data "
            f"({', '.join(mismatches)}); rebuild it"
        )
    vectors = _validate_vectors(vectors, len(metadata["documents"]))
    if metadata.get("vector_count") != vectors.shape[0]:
        raise VectorIndexError("Vector count metadata does not match stored vectors")
    if metadata.get("vector_dimension") != vectors.shape[1]:
        raise VectorIndexError("Vector dimension metadata does not match stored vectors")
    source_ids = [document.get("source_id") for document in metadata["documents"]]
    if any(not source_id for source_id in source_ids) or len(source_ids) != len(set(source_ids)):
        raise VectorIndexError("Vector document metadata has missing/duplicate source IDs")
    return vectors, metadata


def _document_to_knowledge_item(document: dict, score: float) -> dict:
    knowledge_ids = list(document["knowledge_ids"])
    titles = list(document["knowledge_titles"])
    excerpt = document["excerpt"]
    return {
        "knowledge_id": knowledge_ids[0] if knowledge_ids else "",
        "knowledge_ids": knowledge_ids,
        "title": " / ".join(titles) or document["locator"],
        "dynasty": " / ".join(document["periods"]),
        "time": "",
        "people": [],
        "event": excerpt,
        "reason": "",
        "impact": "",
        "content": excerpt,
        "keywords": [],
        "matched_terms": [],
        "score": float(score),
        "retrieval_mode": "vector",
        "retrieval_unit": "source_excerpt",
        "book_id": document["book_id"],
        "book_title": document["book_title"],
        "unit_id": document["unit_id"],
        "unit_title": document["unit_title"],
        "lesson_id": document["lesson_id"],
        "lesson_number": document["lesson_number"],
        "lesson_title": document["lesson_title"],
        "section_title": document["section_title"],
        "material_types": [document["material_type"]],
        "textbook_pages": document["textbook_pages"],
        "pdf_pages": document["pdf_pages"],
        "qualifiers": list(document["qualifiers"]),
        "evidence_type": "textbook_excerpt",
        "certainty": " / ".join(document["certainty_notes"]),
        "source_refs": [
            {
                "source_id": document["source_id"],
                "lesson_id": document["lesson_id"],
                "section_id": document["section_id"],
                "material_type": document["material_type"],
                "textbook_pages": document["textbook_pages"],
                "pdf_pages": document["pdf_pages"],
                "excerpt": excerpt,
                "locator": document["locator"],
            }
        ],
    }


def retrieve_textbook_vectors(question: str, top_k: int = 3) -> list[dict]:
    """Return source-level semantic neighbors; no threshold or fallback is applied."""
    query = question.strip()
    if not query:
        return []
    vectors, metadata = load_vector_index()
    model = get_embedding_model()
    query_text = f"{QUERY_PREFIX}{query}"
    tokenizer = getattr(model, "tokenizer", None)
    max_length = int(getattr(model, "max_seq_length", 0) or 0)
    if tokenizer is None or max_length <= 0:
        raise VectorIndexError("Embedding model does not expose tokenizer/max_seq_length")
    token_count = len(
        tokenizer(query_text, add_special_tokens=True, truncation=False)["input_ids"]
    )
    if token_count > max_length:
        raise VectorIndexError(
            f"Query has {token_count} tokens, exceeding model limit {max_length}"
        )
    try:
        query_vector = model.encode(
            [query_text],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
    except Exception as exc:
        raise VectorIndexError(f"Failed to encode query: {exc}") from exc
    query_vector = _validate_vectors(query_vector, 1)[0]
    scores = vectors @ query_vector
    order = np.argsort(-scores, kind="stable")[: max(0, min(top_k, len(scores)))]
    return [
        _document_to_knowledge_item(metadata["documents"][int(index)], scores[index])
        for index in order
    ]
