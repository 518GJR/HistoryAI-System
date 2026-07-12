"""Import local history knowledge JSON data into MySQL.

Run from the backend directory:
    python -m app.scripts.import_history_knowledge

The importer updates existing rows by title and inserts missing rows. The JSON
file remains the fallback knowledge base for the v0.4 question-answering flow.
"""

import json
from pathlib import Path
from typing import Any

from app.database import SessionLocal
from app.models import HistoryKnowledge

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_FILE = PROJECT_ROOT / "data" / "history_knowledge.json"


def _json_text(value: Any) -> str:
    """Serialize list-like fields for storage in Text columns."""
    if value is None:
        value = []
    if isinstance(value, str):
        value = [value] if value.strip() else []
    return json.dumps(value, ensure_ascii=False)


def _load_json_data() -> list[dict]:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"History knowledge file not found: {DATA_FILE}")

    with DATA_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("history_knowledge.json must contain a list of knowledge items.")

    return data


def import_history_knowledge() -> tuple[int, int]:
    """Import JSON knowledge items into MySQL.

    Returns:
        A tuple of (inserted_count, updated_count).
    """
    inserted_count = 0
    updated_count = 0
    db = SessionLocal()

    try:
        for item in _load_json_data():
            title = str(item.get("title", "")).strip()
            content = str(item.get("content", "")).strip()

            if not title or not content:
                continue

            knowledge = (
                db.query(HistoryKnowledge)
                .filter(HistoryKnowledge.title == title)
                .first()
            )

            values = {
                "title": title,
                "dynasty": item.get("dynasty") or "",
                "time": item.get("time") or "",
                "people": _json_text(item.get("people")),
                "event": item.get("event") or "",
                "reason": item.get("reason") or "",
                "impact": item.get("impact") or "",
                "keywords": _json_text(item.get("keywords")),
                "content": content,
            }

            if knowledge is None:
                db.add(HistoryKnowledge(**values))
                inserted_count += 1
            else:
                for field, value in values.items():
                    setattr(knowledge, field, value)
                updated_count += 1

        db.commit()
        return inserted_count, updated_count
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    inserted, updated = import_history_knowledge()
    print(f"History knowledge import completed. inserted={inserted}, updated={updated}")
