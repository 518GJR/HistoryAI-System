from app.services import rag_service
from app.services.support_assessment import (
    assess_support,
    evidence_covers_assessment,
    supporting_answer_items,
)


def _textbook(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_MODE", "textbook")
    monkeypatch.setenv("RETRIEVAL_MODE", "keyword")
    return rag_service.load_textbook_knowledge_from_json()


def test_unrelated_nearest_neighbors_are_not_treated_as_support(monkeypatch):
    points = _textbook(monkeypatch)
    point_map = {point["knowledge_id"]: point for point in points}
    candidates = []
    for knowledge_id in ("H7A-L02-013", "H7A-L03-015", "H7A-L02-010"):
        point = point_map[knowledge_id]
        candidate = dict(point)
        candidate.update(
            {
                "knowledge_ids": [knowledge_id],
                "retrieval_mode": "vector",
                "retrieval_unit": "source_excerpt",
                "score": 0.5,
            }
        )
        candidates.append(candidate)

    assessment = assess_support(
        "秦始皇统一六国采取了哪些措施？", "vector", candidates, points
    )

    assert assessment.status == "insufficient"
    assert "subject:textbook_topic" in assessment.unsupported_facets
    assert assessment.supporting_source_ids == []


def test_normal_fact_and_paraphrase_are_not_rejected(monkeypatch):
    points = _textbook(monkeypatch)
    questions = (
        "北京人用火有什么作用？",
        "掌握火给北京人的生存带来了哪些好处？",
        "仰韶文化分布在哪里，距今多少年？",
    )

    for question in questions:
        candidates = rag_service.retrieve_history_knowledge(question)
        assessment = assess_support(question, "keyword", candidates, points)
        assert assessment.status == "sufficient", question
        assert assessment.unsupported_facets == [], question
        assert assessment.supporting_source_ids, question


def test_comparison_requires_both_named_sides(monkeypatch):
    points = _textbook(monkeypatch)
    candidates = rag_service.retrieve_history_knowledge(
        "北京人与山顶洞人在工具制作方面有什么不同？"
    )
    only_beijing = [
        item for item in candidates if item["knowledge_id"] == "H7A-L01-009"
    ]

    assessment = assess_support(
        "北京人与山顶洞人在工具制作方面有什么不同？",
        "keyword",
        only_beijing,
        points,
    )

    assert assessment.status == "partial"
    assert "subject:山顶洞人" in assessment.unsupported_facets
    assert "comparison:all_subjects" in assessment.unsupported_facets


def test_used_evidence_must_cover_every_comparison_facet(monkeypatch):
    points = _textbook(monkeypatch)
    question = "北京人与山顶洞人在工具制作方面有什么不同？"
    candidates = rag_service.retrieve_history_knowledge(question)
    assessment = assess_support(question, "keyword", candidates, points)

    assert assessment.status == "sufficient"
    assert not evidence_covers_assessment(
        assessment,
        [{"knowledge_ids": ["H7A-L01-009"]}],
    )
    assert evidence_covers_assessment(
        assessment,
        [
            {"knowledge_ids": ["H7A-L01-009"]},
            {"knowledge_ids": ["H7A-L01-013"]},
        ],
    )


def test_answer_input_contains_only_supporting_verbatim_sources(monkeypatch):
    points = _textbook(monkeypatch)
    question = "北京人用火有什么作用？"
    candidates = rag_service.retrieve_history_knowledge(question)
    assessment = assess_support(question, "keyword", candidates, points)

    answer_items = supporting_answer_items(candidates, assessment)

    assert [item["knowledge_id"] for item in answer_items] == ["H7A-L01-010"]
    assert answer_items[0]["event"] == answer_items[0]["source_refs"][0]["excerpt"]
    assert answer_items[0]["content"] == answer_items[0]["source_refs"][0]["excerpt"]
    assert answer_items[0]["reason"] == ""
    assert answer_items[0]["impact"] == ""
