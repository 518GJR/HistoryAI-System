import json

import httpx

from app.services import ai_service


def _enable_ai(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openai_compatible")
    monkeypatch.setenv("AI_API_KEY", "test-key")
    monkeypatch.setenv("AI_MODEL", "test-model")
    monkeypatch.setenv("AI_BASE_URL", "https://mock.example/v1")


def test_ai_answer_uses_retrieved_sources_with_mock_transport(monkeypatch):
    _enable_ai(monkeypatch)

    def handler(request):
        assert request.url.path == "/v1/chat/completions"
        payload = json.loads(request.content)
        system_prompt = payload["messages"][0]["content"]
        user_payload = json.loads(payload["messages"][1]["content"])
        assert payload["temperature"] == 0
        assert "教材证据选择器" in system_prompt
        assert "只返回严格JSON" in system_prompt
        assert user_payload["source_titles"] == ["秦始皇统一六国"]
        assert user_payload["evidence_lines"][0] == {
            "id": "E1",
            "text": "秦灭六国。",
            "knowledge_id": "QIN-001",
            "knowledge_ids": ["QIN-001"],
            "source_ids": ["SRC-QIN"],
            "source_index": 1,
            "source_title": "秦始皇统一六国",
            "source_titles": ["秦始皇统一六国"],
            "textbook_pages": "",
            "pdf_pages": "",
            "evidence_kind": "textbook_excerpt",
        }
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"selected_ids":["E1"]}'}}]},
        )

    monkeypatch.setattr(
        ai_service,
        "_create_client",
        lambda timeout: httpx.Client(transport=httpx.MockTransport(handler), timeout=timeout),
    )
    answer, mode, used_evidence = ai_service.generate_answer_result(
        "秦始皇为什么统一六国？",
        [
            {
                "knowledge_id": "QIN-001",
                "title": "秦始皇统一六国",
                "content": "结构化摘要不得进入证据池。",
                "source_refs": [{"source_id": "SRC-QIN", "excerpt": "秦灭六国。"}],
            }
        ],
    )

    assert mode == "evidence_selection"
    assert answer == "教材原文：\n1. 【秦始皇统一六国】秦灭六国。"
    assert used_evidence[0]["knowledge_id"] == "QIN-001"
    assert used_evidence[0]["source_ids"] == ["SRC-QIN"]


def test_ai_failure_falls_back_to_template(monkeypatch):
    _enable_ai(monkeypatch)

    def handler(request):
        return httpx.Response(500, json={"error": "mock failure"})

    monkeypatch.setattr(
        ai_service,
        "_create_client",
        lambda timeout: httpx.Client(transport=httpx.MockTransport(handler), timeout=timeout),
    )
    answer, mode, used_evidence = ai_service.generate_answer_result(
        "秦始皇",
        [
            {
                "title": "秦始皇统一六国",
                "dynasty": "秦朝",
                "source_refs": [{"source_id": "SRC-QIN", "excerpt": "秦灭六国。"}],
            }
        ],
    )

    assert mode == "fallback"
    assert used_evidence == []
    assert "秦始皇统一六国" in answer


def test_invalid_ai_evidence_selection_falls_back(monkeypatch):
    _enable_ai(monkeypatch)

    def handler(request):
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"selected_ids":["E999"]}'}}]},
        )

    monkeypatch.setattr(
        ai_service,
        "_create_client",
        lambda timeout: httpx.Client(transport=httpx.MockTransport(handler), timeout=timeout),
    )
    answer, mode, used_evidence = ai_service.generate_answer_result(
        "秦始皇统一六国",
        [
            {
                "title": "秦始皇统一六国",
                "event": "秦灭六国。",
                "source_refs": [{"source_id": "SRC-QIN", "excerpt": "秦灭六国。"}],
            }
        ],
    )

    assert mode == "fallback"
    assert used_evidence == [
        {
            "evidence_id": "E1",
            "text": "秦灭六国。",
            "knowledge_id": "",
            "knowledge_ids": [],
            "source_ids": ["SRC-QIN"],
            "source_title": "秦始皇统一六国",
            "source_titles": ["秦始皇统一六国"],
            "textbook_pages": "",
            "pdf_pages": "",
        }
    ]
    assert "秦灭六国" in answer


def test_fallback_tracks_only_verbatim_excerpt_actually_rendered(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "disabled")
    rendered_excerpt = "北京人用火烧烤食物、防寒、照明、驱兽。"
    unused_excerpt = "这段教材原文没有进入模板回答。"

    answer, mode, used_evidence = ai_service.generate_answer_result(
        "北京人用火有什么作用？",
        [
            {
                "knowledge_id": "K-FIRE",
                "knowledge_ids": ["K-FIRE", "K-SURVIVAL"],
                "title": "北京人用火",
                "event": rendered_excerpt,
                "content": rendered_excerpt,
                "source_refs": [
                    {
                        "source_id": "S-FIRE",
                        "excerpt": rendered_excerpt,
                        "textbook_pages": "6",
                        "pdf_pages": "11",
                    }
                ],
            },
            {
                "knowledge_id": "K-UNUSED",
                "title": "未直接引用的候选",
                "content": "这是结构化摘要，不是来源原文。",
                "source_refs": [
                    {
                        "source_id": "S-UNUSED",
                        "excerpt": unused_excerpt,
                        "textbook_pages": "7",
                        "pdf_pages": "12",
                    }
                ],
            },
        ],
    )

    assert mode == "fallback"
    assert rendered_excerpt in answer
    assert unused_excerpt not in answer
    assert used_evidence == [
        {
            "evidence_id": "E1",
            "text": rendered_excerpt,
            "knowledge_id": "K-FIRE",
            "knowledge_ids": ["K-FIRE", "K-SURVIVAL"],
            "source_ids": ["S-FIRE"],
            "source_title": "北京人用火",
            "source_titles": ["北京人用火"],
            "textbook_pages": "6",
            "pdf_pages": "11",
        }
    ]


def test_fallback_deduplicates_same_source_text_and_merges_traceability(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "disabled")
    excerpt = "同一段教材原文。"
    shared_reference = {
        "source_id": "S-1",
        "excerpt": excerpt,
        "textbook_pages": "7",
        "pdf_pages": "12",
    }

    answer, mode, used_evidence = ai_service.generate_answer_result(
        "这段材料说明了什么？",
        [
            {
                "knowledge_id": "K-1",
                "title": "知识点一",
                "content": excerpt,
                "source_refs": [shared_reference],
            },
            {
                "knowledge_id": "K-2",
                "title": "知识点二",
                "content": excerpt,
                "source_refs": [shared_reference],
            },
        ],
    )

    assert mode == "fallback"
    assert excerpt in answer
    assert len(used_evidence) == 1
    assert used_evidence[0]["source_ids"] == ["S-1"]
    assert used_evidence[0]["knowledge_ids"] == ["K-1", "K-2"]
    assert used_evidence[0]["source_titles"] == ["知识点一", "知识点二"]
    assert used_evidence[0]["textbook_pages"] == "7"
    assert used_evidence[0]["pdf_pages"] == "12"


def test_fallback_refusal_has_no_used_evidence(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "disabled")

    answer, mode, used_evidence = ai_service.generate_answer_result("范围外问题", [])

    assert mode == "fallback"
    assert "当前检索资料中暂时没有匹配到" in answer
    assert used_evidence == []


def test_multi_source_selection_preserves_point_source_and_page_mapping(monkeypatch):
    _enable_ai(monkeypatch)

    def handler(request):
        payload = json.loads(request.content)
        user_payload = json.loads(payload["messages"][1]["content"])
        lines = user_payload["evidence_lines"]
        assert [line["knowledge_id"] for line in lines] == ["K-A", "K-B"]
        assert [line["source_ids"] for line in lines] == [["S-A"], ["S-B"]]
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"selected_ids":["E1","E2"]}'}}]},
        )

    monkeypatch.setattr(
        ai_service,
        "_create_client",
        lambda timeout: httpx.Client(transport=httpx.MockTransport(handler), timeout=timeout),
    )

    answer, mode, used_evidence = ai_service.generate_answer_result(
        "甲与乙有什么不同？",
        [
            {
                "knowledge_id": "K-A",
                "title": "甲知识点",
                "event": "结构化甲摘要。",
                "textbook_pages": "11",
                "pdf_pages": "16",
                "source_refs": [
                    {
                        "source_id": "S-A",
                        "excerpt": "甲使用甲工具。",
                        "textbook_pages": "11",
                        "pdf_pages": "16",
                    }
                ],
            },
            {
                "knowledge_id": "K-B",
                "title": "乙知识点",
                "event": "结构化乙摘要。",
                "textbook_pages": "12",
                "pdf_pages": "17",
                "source_refs": [
                    {
                        "source_id": "S-B",
                        "excerpt": "乙使用乙工具。",
                        "textbook_pages": "12",
                        "pdf_pages": "17",
                    }
                ],
            },
        ],
    )

    assert mode == "evidence_selection"
    assert "【甲知识点】甲使用甲工具。" in answer
    assert "【乙知识点】乙使用乙工具。" in answer
    assert used_evidence == [
        {
            "evidence_id": "E1",
            "text": "甲使用甲工具。",
            "knowledge_id": "K-A",
            "knowledge_ids": ["K-A"],
            "source_ids": ["S-A"],
            "source_title": "甲知识点",
            "source_titles": ["甲知识点"],
            "textbook_pages": "11",
            "pdf_pages": "16",
        },
        {
            "evidence_id": "E2",
            "text": "乙使用乙工具。",
            "knowledge_id": "K-B",
            "knowledge_ids": ["K-B"],
            "source_ids": ["S-B"],
            "source_title": "乙知识点",
            "source_titles": ["乙知识点"],
            "textbook_pages": "12",
            "pdf_pages": "17",
        },
    ]


def test_template_answer_leads_with_summary_and_certainty():
    answer = ai_service.template_answer(
        "山顶洞人已经确定会人工取火了吗？",
        [
            {
                "title": "山顶洞人的技术与生活",
                "content": "山顶洞人可能已经知道人工取火。",
                "keywords": ["人工取火"],
                "qualifiers": ["可能"],
                "certainty": "人工取火为可能性表述",
            }
        ],
    )

    assert "直接回答：山顶洞人可能已经知道人工取火。" in answer
    assert "系统确定性说明：根据当前教材证据，不能肯定这一说法" in answer
    assert "人工取火为可能性表述" not in answer


def test_model_selected_possible_fact_gets_separate_certainty_note(monkeypatch):
    _enable_ai(monkeypatch)

    def handler(request):
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"selected_ids":["E1"]}'}}]},
        )

    monkeypatch.setattr(
        ai_service,
        "_create_client",
        lambda timeout: httpx.Client(transport=httpx.MockTransport(handler), timeout=timeout),
    )

    answer, mode, used_evidence = ai_service.generate_answer_result(
        "能不能肯定某人掌握了人工取火？",
        [
            {
                "knowledge_id": "K-1",
                "title": "技术与生活",
                "keywords": ["人工取火"],
                "qualifiers": ["可能"],
                "certainty": "人工取火为可能性表述",
                "source_refs": [
                    {
                        "source_id": "S-1",
                        "excerpt": "他们可能已经知道人工取火。",
                    }
                ],
            }
        ],
    )

    assert mode == "evidence_selection"
    assert answer.startswith(
        "系统确定性说明：根据当前教材证据，不能肯定这一说法；教材使用的是“可能”。"
    )
    assert "教材原文：" in answer
    assert used_evidence[0]["text"] == "他们可能已经知道人工取火。"
    assert "人工取火为可能性表述" not in answer
    assert all("人工取火为可能性表述" not in line["text"] for line in used_evidence)


def test_internal_metadata_never_enters_textbook_evidence_pool():
    lines = ai_service._build_evidence_lines(
        [
            {
                "knowledge_id": "K-1",
                "title": "测试知识点",
                "event": "结构化事件摘要",
                "reason": "结构化原因摘要",
                "impact": "结构化影响摘要",
                "dimensions": {"content": "结构化维度摘要"},
                "certainty": "某事实为可能性表述",
                "source_refs": [
                    {
                        "source_id": "S-1",
                        "excerpt": "这是教材原文。",
                        "textbook_pages": "7",
                        "pdf_pages": "12",
                    }
                ],
            }
        ]
    )

    assert [line["text"] for line in lines] == ["这是教材原文。"]
    assert lines[0]["evidence_kind"] == "textbook_excerpt"


def test_same_source_and_text_is_deduplicated_and_traceability_is_merged():
    shared_reference = {
        "source_id": "S-1",
        "excerpt": "同一段教材原文。",
        "textbook_pages": "7",
        "pdf_pages": "12",
    }

    lines = ai_service._build_evidence_lines(
        [
            {
                "knowledge_id": "K-1",
                "title": "知识点一",
                "source_refs": [shared_reference],
            },
            {
                "knowledge_id": "K-2",
                "title": "知识点二",
                "source_refs": [shared_reference],
            },
        ]
    )

    assert len(lines) == 1
    assert lines[0]["knowledge_ids"] == ["K-1", "K-2"]
    assert lines[0]["source_titles"] == ["知识点一", "知识点二"]
    assert lines[0]["source_ids"] == ["S-1"]
    assert lines[0]["textbook_pages"] == "7"
    assert lines[0]["pdf_pages"] == "12"


def test_different_text_from_same_source_is_not_removed():
    lines = ai_service._build_evidence_lines(
        [
            {
                "knowledge_id": "K-1",
                "title": "知识点一",
                "source_refs": [{"source_id": "S-1", "excerpt": "证据甲。"}],
            },
            {
                "knowledge_id": "K-2",
                "title": "知识点二",
                "source_refs": [{"source_id": "S-1", "excerpt": "证据乙。"}],
            },
        ]
    )

    assert [line["text"] for line in lines] == ["证据甲。", "证据乙。"]


def test_certainty_note_requires_the_uncertain_fact_to_match_the_question():
    item = {
        "knowledge_id": "K-1",
        "keywords": ["阶级分化", "尧都"],
        "qualifiers": ["很有可能"],
        "certainty": "尧都为可能性判断",
    }
    evidence = [
        {
            "knowledge_ids": ["K-1"],
            "text": "阶级分化已经相当明显；有学者认为这里很有可能是尧都。",
        }
    ]

    assert (
        ai_service._certainty_note(
            "能不能确定这里已经出现阶级分化？", [item], evidence
        )
        == ""
    )


def test_certain_fact_and_ordinary_question_are_not_incorrectly_denied():
    certain_item = {
        "knowledge_id": "K-1",
        "keywords": ["使用火"],
        "qualifiers": [],
        "certainty": "教材明确说明",
    }
    possible_item = {
        "knowledge_id": "K-2",
        "keywords": ["人工取火"],
        "qualifiers": ["可能"],
        "certainty": "人工取火为可能性表述",
    }

    assert ai_service._certainty_note(
        "能不能确定北京人已经会使用火？", [certain_item], None
    ) == ""
    assert ai_service._certainty_note(
        "山顶洞人人工取火的教材表述是什么？", [possible_item], None
    ) == ""
