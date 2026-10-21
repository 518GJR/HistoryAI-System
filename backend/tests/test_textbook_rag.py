import json

import pytest

from app.services import rag_service


def test_textbook_dataset_loads_all_48_stable_ids(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_MODE", "textbook")

    items = rag_service.load_history_knowledge()

    assert len(items) == 48
    assert len({item["knowledge_id"] for item in items}) == 48
    assert items[0]["knowledge_id"] == "H7A-L01-001"
    assert items[-1]["knowledge_id"] == "H7A-L03-016"
    assert all(item["source_refs"] for item in items)


def test_textbook_sources_are_reusable_and_publication_unknowns_stay_blank():
    payload = json.loads(rag_service.TEXTBOOK_DATA_FILE.read_text(encoding="utf-8"))

    assert len(payload["sources"]) == 35
    assert len(payload["sources"]) < len(payload["knowledge_points"])
    assert payload["book"]["edition"] == ""
    assert payload["book"]["isbn"] == ""
    assert payload["book"]["bibliographic_status"] == "待补"
    assert all("NÅO" not in source["excerpt"] for source in payload["sources"])


def test_textbook_path_is_independent_of_process_working_directory(monkeypatch, tmp_path):
    monkeypatch.setenv("KNOWLEDGE_MODE", "textbook")
    monkeypatch.chdir(tmp_path)

    items = rag_service.load_history_knowledge()

    assert len(items) == 48


def test_textbook_mode_does_not_query_or_fallback_to_demo_database(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_MODE", "textbook")

    def fail_if_called():
        raise AssertionError("demo database must not be read in textbook mode")

    monkeypatch.setattr(rag_service, "load_history_knowledge_from_db", fail_if_called)

    items = rag_service.load_history_knowledge()

    assert len(items) == 48
    assert all(item.get("book_id") == "H7A" for item in items)


def test_demo_mode_keeps_database_priority(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_MODE", "demo")
    database_item = {"title": "数据库演示条目", "keywords": ["数据库"]}
    monkeypatch.setattr(
        rag_service, "load_history_knowledge_from_db", lambda: [database_item]
    )

    assert rag_service.load_history_knowledge() == [database_item]


def test_textbook_retrieval_carries_traceable_source_metadata(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_MODE", "textbook")

    results = rag_service.retrieve_history_knowledge("北京人用火有什么作用？")

    assert results
    source = rag_service.knowledge_item_to_source(results[0])
    assert source["knowledge_id"].startswith("H7A-L01-")
    assert source["book_title"]
    assert source["lesson_number"] == 1
    assert source["lesson_title"]
    assert source["section_title"]
    assert source["textbook_pages"]
    assert source["pdf_pages"]
    assert source["source_refs"][0]["excerpt"]


def test_specific_textbook_term_wins_score_tie(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_MODE", "textbook")

    results = rag_service.retrieve_history_knowledge("山顶洞人已经确定会人工取火了吗？")

    assert results[0]["title"] == "山顶洞人的技术与生活"
    assert "人工取火" in results[0]["matched_terms"]
    assert results[0]["certainty"] == "人工取火为可能性表述"


@pytest.mark.parametrize(
    ("question", "required_ids"),
    [
        (
            "北京人与山顶洞人在工具制作方面有什么不同？",
            {"H7A-L01-009", "H7A-L01-013"},
        ),
        (
            "河姆渡人与半坡人的主要农作物和房屋有什么不同？",
            {"H7A-L02-007", "H7A-L02-012"},
        ),
        (
            "良渚古城与陶寺古城的发现分别说明了什么？",
            {"H7A-L03-006", "H7A-L03-008"},
        ),
    ],
)
def test_comparison_retrieval_keeps_both_subjects_in_top_three(
    monkeypatch, question, required_ids
):
    monkeypatch.setenv("KNOWLEDGE_MODE", "textbook")

    results = rag_service.retrieve_history_knowledge(question)

    assert len(results) == 3
    assert required_ids.issubset({item["knowledge_id"] for item in results})


@pytest.mark.parametrize(
    ("question", "expected_first_id"),
    [
        ("北京人用火有什么作用？", "H7A-L01-010"),
        ("仰韶文化的分布、年代和主要特征是什么？", "H7A-L02-010"),
        ("山顶洞人已经确定会人工取火了吗？", "H7A-L01-013"),
    ],
)
def test_dimension_ranking_keeps_single_subject_queries_stable(
    monkeypatch, question, expected_first_id
):
    monkeypatch.setenv("KNOWLEDGE_MODE", "textbook")

    results = rag_service.retrieve_history_knowledge(question)

    assert results[0]["knowledge_id"] == expected_first_id


def test_textbook_no_match_does_not_fallback_to_demo_data(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_MODE", "textbook")

    results = rag_service.retrieve_history_knowledge("秦始皇统一六国")

    assert results == []


@pytest.mark.parametrize("contents", ["not json", json.dumps([])])
def test_textbook_invalid_data_fails_explicitly(monkeypatch, tmp_path, contents):
    invalid_file = tmp_path / "textbook.json"
    invalid_file.write_text(contents, encoding="utf-8")
    monkeypatch.setenv("KNOWLEDGE_MODE", "textbook")
    monkeypatch.setattr(rag_service, "TEXTBOOK_DATA_FILE", invalid_file)

    with pytest.raises(rag_service.KnowledgeDataError):
        rag_service.load_history_knowledge()


def test_textbook_missing_file_fails_explicitly(monkeypatch, tmp_path):
    monkeypatch.setenv("KNOWLEDGE_MODE", "textbook")
    monkeypatch.setattr(rag_service, "TEXTBOOK_DATA_FILE", tmp_path / "missing.json")

    with pytest.raises(rag_service.KnowledgeDataError):
        rag_service.load_history_knowledge()
