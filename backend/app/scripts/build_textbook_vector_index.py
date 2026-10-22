"""Explicit CLI for building the local textbook vector index."""

import json

from app.services.vector_service import build_vector_index, configured_index_file


def main() -> None:
    metadata = build_vector_index()
    print(
        json.dumps(
            {
                "index_file": str(configured_index_file()),
                "model_id": metadata["model_id"],
                "model_revision": metadata["model_revision"],
                "vector_count": metadata["vector_count"],
                "vector_dimension": metadata["vector_dimension"],
                "textbook_data_sha256": metadata["textbook_data_sha256"],
                "maximum_document_tokens": metadata["maximum_document_tokens"],
                "model_max_tokens": metadata["model_max_tokens"],
                "built_at": metadata["built_at"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
