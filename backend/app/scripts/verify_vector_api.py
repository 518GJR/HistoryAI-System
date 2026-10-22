"""Call a running API and save a small vector-integration evidence report."""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


CASES = [
    {"id": "API-V01", "category": "in_scope", "question": "北京人用火有什么作用？"},
    {
        "id": "API-V02",
        "category": "out_of_scope",
        "question": "秦始皇统一六国采取了哪些措施？",
    },
]


def _request_json(url: str, method: str = "GET", payload: dict | None = None) -> dict:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"API request failed: {method} {url}: {exc}") from exc


def _source_has_traceable_excerpt(source: dict) -> bool:
    return bool(
        source.get("textbook_pages")
        and source.get("pdf_pages")
        and any(
            reference.get("source_id")
            and reference.get("excerpt")
            and reference.get("textbook_pages")
            and reference.get("pdf_pages")
            for reference in source.get("source_refs") or []
            if isinstance(reference, dict)
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    health = _request_json(f"{args.base_url}/")
    report = {
        "verification_type": "running_api_real_local_embedding_integration",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": args.base_url,
        "database_url": os.getenv("DATABASE_URL", ""),
        "providers": {
            "ai": os.getenv("AI_PROVIDER", ""),
            "asr": os.getenv("ASR_PROVIDER", ""),
            "tts": os.getenv("TTS_PROVIDER", ""),
        },
        "embedding_execution": "real_local_cpu_cached_offline",
        "health": health,
        "cases": [],
    }
    for case in CASES:
        started = time.perf_counter()
        response = _request_json(
            f"{args.base_url}/api/question",
            method="POST",
            payload={"question": case["question"]},
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        sources = response.get("sources") or []
        used_evidence = response.get("used_evidence") or []
        checks = {
            "actual_mode_is_vector": response.get("retrieval_mode") == "vector",
            "all_sources_marked_vector": bool(sources)
            and all(source.get("retrieval_mode") == "vector" for source in sources),
            "sources_have_traceable_excerpt_and_pages": bool(sources)
            and all(_source_has_traceable_excerpt(source) for source in sources),
            "used_evidence_present": bool(used_evidence),
        }
        if case["category"] == "out_of_scope":
            refusal_markers = ("暂时没有匹配到", "资料不足", "无法回答", "不能回答")
            checks["out_of_scope_answer_refuses"] = any(
                marker in str(response.get("answer") or "") for marker in refusal_markers
            )
            checks["out_of_scope_has_no_adopted_evidence"] = not used_evidence
        report["cases"].append(
            {
                **case,
                "elapsed_ms": round(elapsed_ms, 3),
                "checks": checks,
                "response": response,
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise RuntimeError(f"Refusing to overwrite existing report: {args.output}")
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
