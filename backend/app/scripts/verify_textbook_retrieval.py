"""Run local keyword/vector retrieval only and save raw comparable results."""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from app.services import rag_service
from app.services.vector_service import (
    configured_index_file,
    load_vector_index,
)


DEFAULT_QUESTIONS = [
    {
        "id": "V01",
        "category": "fact",
        "question": "北京人用火有什么作用？",
        "comparison_source_ids": [],
    },
    {
        "id": "V02",
        "category": "paraphrase",
        "question": "掌握火给北京人的生存带来了哪些好处？",
        "comparison_source_ids": [],
    },
    {
        "id": "V03",
        "category": "fact",
        "question": "仰韶文化分布在哪里，距今多少年？",
        "comparison_source_ids": [],
    },
    {
        "id": "V04",
        "category": "comparison",
        "question": "北京人与山顶洞人在工具制作方面有什么不同？",
        "comparison_source_ids": ["H7A-P006-A", "H7A-P007-A"],
    },
    {
        "id": "V05",
        "category": "comparison",
        "question": "河姆渡人与半坡人的主要农作物和房屋有什么不同？",
        "comparison_source_ids": ["H7A-P011-A", "H7A-P012-B"],
    },
    {
        "id": "V06",
        "category": "out_of_scope",
        "question": "秦始皇统一六国采取了哪些措施？",
        "comparison_source_ids": [],
    },
]


def _result_snapshot(item: dict, rank: int) -> dict:
    return {
        "rank": rank,
        "score": float(item.get("score", 0)),
        "source_ids": [
            str(reference.get("source_id") or "")
            for reference in item.get("source_refs") or []
            if isinstance(reference, dict)
        ],
        "knowledge_ids": list(
            item.get("knowledge_ids")
            or ([item.get("knowledge_id")] if item.get("knowledge_id") else [])
        ),
        "title": str(item.get("title") or ""),
        "textbook_pages": str(item.get("textbook_pages") or ""),
        "pdf_pages": str(item.get("pdf_pages") or ""),
        "retrieval_unit": str(item.get("retrieval_unit") or "knowledge_point"),
    }


def run_verification() -> dict:
    _, index_metadata = load_vector_index()
    report = {
        "verification_type": "real_local_embedding_retrieval",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ai_provider": "disabled",
        "asr_provider": "disabled",
        "tts_provider": "disabled",
        "model_id": index_metadata["model_id"],
        "model_revision": index_metadata["model_revision"],
        "index_file": str(configured_index_file()),
        "index_format_version": index_metadata["format_version"],
        "vector_count": index_metadata["vector_count"],
        "vector_dimension": index_metadata["vector_dimension"],
        "textbook_data_sha256": index_metadata["textbook_data_sha256"],
        "similarity": index_metadata["similarity"],
        "normalization": index_metadata["normalization"],
        "top_k": rag_service.TOP_K,
        "top_k_unit_note": {
            "keyword": "knowledge_point",
            "vector": "deduplicated_source_excerpt",
        },
        "score_warning": (
            "Vector cosine similarity is a ranking score, not answer correctness "
            "probability or a validated sufficiency threshold."
        ),
        "questions": [],
    }
    for case in DEFAULT_QUESTIONS:
        case_report = {**case, "runs": {}}
        for mode in ("keyword", "vector"):
            os.environ["KNOWLEDGE_MODE"] = "textbook"
            os.environ["RETRIEVAL_MODE"] = mode
            started = time.perf_counter()
            results = rag_service.retrieve_history_knowledge(case["question"])
            elapsed_ms = (time.perf_counter() - started) * 1000
            snapshots = [
                _result_snapshot(item, rank)
                for rank, item in enumerate(results, start=1)
            ]
            candidate_sources = {
                source_id
                for result in snapshots
                for source_id in result["source_ids"]
            }
            expected = set(case["comparison_source_ids"])
            case_report["runs"][mode] = {
                "actual_mode": mode,
                "elapsed_ms": round(elapsed_ms, 3),
                "results": snapshots,
                "comparison_both_sides_in_candidates": (
                    expected.issubset(candidate_sources) if expected else None
                ),
            }
        report["questions"].append(case_report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run_verification()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
