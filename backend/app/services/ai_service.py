"""RAG answer generation with an external-model fallback strategy."""

import json
import logging
import re

import httpx

from app.services.provider_config import provider_config


logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是教材证据选择器，不负责自由生成答案。
用户消息会提供一个问题和若干带编号的教材证据行。
请选择1—6条最直接回答问题的证据；比较或“分别说明”类问题必须覆盖问题明确提到的各方。
只返回严格JSON：{"selected_ids":["E1"]}。
不得输出解释、Markdown、代码块或证据编号以外的内容，不得创造不存在的编号。"""


def _build_evidence_lines(items: list[dict]) -> list[dict]:
    """Build deduplicated textbook excerpts, excluding derived metadata."""
    lines = []
    lines_by_source_text = {}
    for source_index, item in enumerate(items, start=1):
        knowledge_id = str(item.get("knowledge_id") or "")
        knowledge_ids = [
            str(value) for value in (item.get("knowledge_ids") or [knowledge_id]) if value
        ]
        source_title = str(item.get("title") or "")
        for reference in item.get("source_refs", []):
            if not isinstance(reference, dict):
                continue
            source_id = str(reference.get("source_id") or "").strip()
            text = str(reference.get("excerpt") or "").strip()
            if not source_id or not text:
                continue

            dedupe_key = (source_id, text)
            existing = lines_by_source_text.get(dedupe_key)
            if existing is not None:
                for associated_id in knowledge_ids:
                    if associated_id not in existing["knowledge_ids"]:
                        existing["knowledge_ids"].append(associated_id)
                if source_title and source_title not in existing["source_titles"]:
                    existing["source_titles"].append(source_title)
                continue

            line = {
                "id": f"E{len(lines) + 1}",
                "text": text,
                "knowledge_id": knowledge_id,
                "knowledge_ids": knowledge_ids,
                "source_ids": [source_id],
                "source_index": source_index,
                "source_title": source_title,
                "source_titles": [source_title] if source_title else [],
                "textbook_pages": str(reference.get("textbook_pages") or ""),
                "pdf_pages": str(reference.get("pdf_pages") or ""),
                "evidence_kind": "textbook_excerpt",
            }
            lines.append(line)
            lines_by_source_text[dedupe_key] = line
    return lines


def _is_certainty_question(question: str) -> bool:
    if not any(term in question for term in ("确定", "肯定", "证实", "确认")):
        return False
    return bool(
        re.search(r"能否|能不能|是否|是不是|可否|已经|是否已经|吗|[？?]", question)
    )


def _certainty_note(
    question: str,
    knowledge_items: list[dict],
    selected_evidence: list[dict] | None,
) -> str:
    """Return a conservative system inference only for a linked possible fact."""
    if not _is_certainty_question(question):
        return ""

    selected_knowledge_ids = None
    selected_texts = []
    if selected_evidence is not None:
        selected_knowledge_ids = {
            knowledge_id
            for evidence in selected_evidence
            for knowledge_id in evidence.get("knowledge_ids", [])
        }
        selected_texts = [str(evidence.get("text") or "") for evidence in selected_evidence]

    for item in knowledge_items:
        knowledge_id = str(item.get("knowledge_id") or "")
        if selected_knowledge_ids is not None and knowledge_id not in selected_knowledge_ids:
            continue

        certainty = str(item.get("certainty") or "")
        if "可能" not in certainty:
            continue
        keywords = item.get("keywords", [])
        if isinstance(keywords, str):
            keywords = [keywords]
        linked_facts = [
            keyword
            for keyword in keywords
            if len(str(keyword)) >= 2
            and str(keyword) in question
            and str(keyword) in certainty
        ]
        if not linked_facts:
            continue

        qualifiers = item.get("qualifiers", [])
        if isinstance(qualifiers, str):
            qualifiers = [qualifiers]
        possible_qualifiers = [
            str(qualifier)
            for qualifier in qualifiers
            if "可能" in str(qualifier)
        ]
        if not possible_qualifiers:
            continue
        qualifier = possible_qualifiers[0]
        if selected_texts and not any(
            fact in text and qualifier in text
            for fact in linked_facts
            for text in selected_texts
        ):
            continue
        return f"根据当前教材证据，不能肯定这一说法；教材使用的是“{qualifier}”。"
    return ""


def _answer_from_selected_evidence(
    raw_answer: str, evidence_lines: list[dict]
) -> tuple[str, list[dict]]:
    """Validate model-selected IDs and assemble an evidence-only answer."""
    payload = json.loads(raw_answer)
    selected_ids = payload.get("selected_ids")
    if not isinstance(selected_ids, list) or not 1 <= len(selected_ids) <= 6:
        raise ValueError("AI provider returned invalid evidence selection")

    evidence_map = {line["id"]: line for line in evidence_lines}
    selected_lines = []
    selected_keys = set()
    for selected_id in selected_ids:
        if not isinstance(selected_id, str) or selected_id not in evidence_map:
            raise ValueError("AI provider selected unknown evidence")
        line = evidence_map[selected_id]
        selected_key = (tuple(line["source_ids"]), line["text"])
        if selected_key not in selected_keys:
            selected_keys.add(selected_key)
            selected_lines.append(
                {
                    "evidence_id": line["id"],
                    "text": line["text"],
                    "knowledge_id": line["knowledge_id"],
                    "knowledge_ids": line["knowledge_ids"],
                    "source_ids": line["source_ids"],
                    "source_title": line["source_title"],
                    "source_titles": line["source_titles"],
                    "textbook_pages": line["textbook_pages"],
                    "pdf_pages": line["pdf_pages"],
                }
            )
    if not selected_lines:
        raise ValueError("AI provider selected no evidence")

    body = "\n".join(
        f"{index}. 【{' / '.join(line['source_titles'])}】{line['text']}"
        if line["source_titles"]
        else f"{index}. {line['text']}"
        for index, line in enumerate(selected_lines, start=1)
    )
    return f"教材原文：\n{body}", selected_lines


def template_answer(question: str, knowledge_items: list[dict]) -> str:
    """根据检索到的历史知识生成回答，作为未配置模型或模型调用失败时的 fallback。"""
    if not knowledge_items:
        return (
            f"你提出的问题是：{question}。"
            "当前检索资料中暂时没有匹配到足以回答这一问题的知识点。"
            "这不表示整本教材或知识库没有相关内容；可以换用教材中的人物、遗址、课次或事件名称继续检索。"
        )

    main_item = knowledge_items[0]
    direct_answer = main_item.get("content") or main_item.get("event") or ""
    certainty_note = _certainty_note(question, knowledge_items, None)

    answer_parts = [
        f"你提出的问题是：{question}",
        "根据当前历史知识库，找到以下相关内容：",
    ]
    if direct_answer:
        answer_parts.append(f"直接回答：{direct_answer}")
    if certainty_note:
        answer_parts.append(f"系统确定性说明：{certainty_note}")

    for index, item in enumerate(knowledge_items, start=1):
        title = item.get("title", "未命名知识点")
        dynasty = item.get("dynasty") or "未标注朝代"
        time = item.get("time") or "时间未标注"
        event = item.get("event") or item.get("content", "")
        reason = item.get("reason") or "当前知识库暂未补充原因说明。"
        impact = item.get("impact") or "当前知识库暂未补充影响说明。"
        content = item.get("content", "")
        matched_terms = "、".join(item.get("matched_terms", []))
        score = item.get("score", 0)
        locator_parts = [
            item.get("book_title", ""),
            f'第{item["lesson_number"]}课' if item.get("lesson_number") else "",
            item.get("section_title", ""),
            f'教材第{item["textbook_pages"]}页' if item.get("textbook_pages") else "",
            f'PDF页序{item["pdf_pages"]}' if item.get("pdf_pages") else "",
        ]
        locator = " · ".join(part for part in locator_parts if part)

        answer_parts.append(
            f"{index}. {title}（{dynasty}，{time}）\n"
            f"事件：{event}\n"
            f"原因：{reason}\n"
            f"影响：{impact}\n"
            f"补充：{content}\n"
            f"来源：{locator or '当前演示知识库'}\n"
            f"匹配关键词：{matched_terms or '无'}；相关度分数：{score}。"
        )

    answer_parts.append("你可以继续追问某个事件的原因、影响或时间线。")
    return "\n".join(answer_parts)


def _create_client(timeout: float) -> httpx.Client:
    """为自动测试提供安装 httpx.MockTransport 的替换点。"""
    return httpx.Client(timeout=timeout)


def generate_answer_result(
    question: str, knowledge_items: list[dict]
) -> tuple[str, str, list[dict]]:
    """Return answer, generation path, and the evidence actually used."""
    config = provider_config("AI")
    if not knowledge_items or not config:
        return template_answer(question, knowledge_items), "fallback", []

    # The model selects from verbatim evidence attached to all retrieved
    # points. The backend, not the model, assembles the final answer text.
    evidence_lines = _build_evidence_lines(knowledge_items)
    if not evidence_lines:
        return template_answer(question, knowledge_items), "fallback", []
    try:
        with _create_client(config["timeout"]) as client:
            response = client.post(
                f'{config["url"]}/chat/completions',
                headers={"Authorization": f'Bearer {config["key"]}'},
                json={
                    "model": config["model"],
                    "temperature": 0,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": json.dumps(
                                {
                                    "question": question,
                                    "source_titles": [
                                        item.get("title", "") for item in knowledge_items
                                    ],
                                    "evidence_lines": evidence_lines,
                                },
                                ensure_ascii=False,
                            ),
                        },
                    ],
                },
            )
            response.raise_for_status()
            answer = response.json()["choices"][0]["message"]["content"]
            if not isinstance(answer, str) or not answer.strip():
                raise ValueError("AI provider returned an empty answer")
            assembled_answer, selected_evidence = _answer_from_selected_evidence(
                answer, evidence_lines
            )
            certainty_note = _certainty_note(
                question, knowledge_items, selected_evidence
            )
            if certainty_note:
                assembled_answer = (
                    f"系统确定性说明：{certainty_note}\n{assembled_answer}"
                )
            return assembled_answer, "evidence_selection", selected_evidence
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
        logger.warning("AI request failed; using knowledge template: %s", exc)
        return template_answer(question, knowledge_items), "fallback", []


def generate_answer(question: str, knowledge_items: list[dict]) -> str:
    """兼容原有调用方，仅返回回答文本。"""
    return generate_answer_result(question, knowledge_items)[0]
