"""Run frozen support-gate cases with disabled providers and an isolated DB."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import time

from fastapi.testclient import TestClient
import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app


def _source_snapshot(source) -> dict:
    return {
        "title": source["title"],
        "score": source["score"],
        "retrieval_mode": source["retrieval_mode"],
        "retrieval_unit": source["retrieval_unit"],
        "knowledge_ids": source["knowledge_ids"],
        "source_ids": [reference["source_id"] for reference in source["source_refs"]],
        "source_refs": source["source_refs"],
        "supporting": source["supporting"],
        "used_evidence": source["used_evidence"],
    }


def run_verification(case_file: Path) -> dict:
    os.environ["KNOWLEDGE_MODE"] = "textbook"
    for prefix in ("AI", "ASR", "TTS"):
        os.environ[f"{prefix}_PROVIDER"] = "disabled"
        os.environ[f"{prefix}_API_KEY"] = ""

    case_payload = json.loads(case_file.read_text(encoding="utf-8"))
    cases = case_payload["cases"]
    original_http_handler = httpx.HTTPTransport.handle_request

    def block_external_http(*args, **kwargs):
        raise RuntimeError("External HTTP is blocked during support verification")

    httpx.HTTPTransport.handle_request = block_external_http
    with tempfile.TemporaryDirectory(prefix="historyai-support-") as directory:
        database_path = Path(directory) / "verification.sqlite3"
        engine = create_engine(f"sqlite:///{database_path.as_posix()}")
        Base.metadata.create_all(bind=engine)
        session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        def override_get_db():
            db = session_factory()
            try:
                yield db
            finally:
                db.close()

        previous_override = app.dependency_overrides.get(get_db)
        app.dependency_overrides[get_db] = override_get_db
        report = {
            "verification_type": "support_assessment_frozen_independent_cases",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "default_retrieval_mode_unchanged": "keyword",
            "providers": {"ai": "disabled", "asr": "disabled", "tts": "disabled"},
            "external_http": "blocked; Hugging Face/Transformers forced offline",
            "database": "test-owned temporary SQLite (removed after run)",
            "cases_were_not_used_to_modify_this_version": True,
            "case_definition": case_payload,
            "top_k": 3,
            "top_k_unit_note": {
                "keyword": "knowledge_point",
                "vector": "deduplicated_source_excerpt"
            },
            "evidence_budget_warning": "Top K units differ; this is not a fair retrieval comparison experiment.",
            "runs": {},
        }
        try:
            with TestClient(app) as client:
                for mode in ("keyword", "vector"):
                    os.environ["RETRIEVAL_MODE"] = mode
                    results = []
                    for case in cases:
                        started = time.perf_counter()
                        http_response = client.post(
                            "/api/question", json={"question": case["question"]}
                        )
                        http_response.raise_for_status()
                        response = http_response.json()
                        results.append(
                            {
                                **case,
                                "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                                "retrieval_mode": response["retrieval_mode"],
                                "answer_mode": response["answer_mode"],
                                "answer": response["answer"],
                                "used_evidence": response["used_evidence"],
                                "support_assessment": response["support_assessment"],
                                "sources": [
                                    _source_snapshot(source) for source in response["sources"]
                                ],
                            }
                        )
                    report["runs"][mode] = {"total": len(results), "cases": results}
            return report
        finally:
            httpx.HTTPTransport.handle_request = original_http_handler
            if previous_override is None:
                app.dependency_overrides.pop(get_db, None)
            else:
                app.dependency_overrides[get_db] = previous_override
            engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError(f"Refusing to overwrite existing report: {args.output}")
    report = run_verification(args.cases)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
