"""Interpretable textbook support checks between retrieval and answering."""

from __future__ import annotations

from dataclasses import dataclass, field
import re


METHOD = "interpretable-v1"
CALIBRATION_VERSION = "development-set-v1"


ASPECT_CUES = {
    "time": ("何时", "什么时候", "年代", "距今", "时间", "多少年"),
    "place": ("哪里", "哪儿", "何处", "地点", "位于", "分布"),
    "reason": ("为什么", "为何", "原因", "背景"),
    "process": ("如何", "怎么", "怎样", "过程", "措施", "方法", "做法"),
    "result_impact": (
        "作用",
        "意义",
        "影响",
        "结果",
        "好处",
        "价值",
        "说明",
        "反映",
        "表明",
        "证实",
    ),
    "certainty": ("确定", "肯定", "证实", "确认", "能否", "能不能", "是否"),
}

COMPARISON_CUES = ("比较", "相比", "不同", "区别", "异同", "分别")
TOPIC_GROUPS = {
    "tools": ("工具", "制作", "技术", "石器", "骨器", "磨光", "钻孔"),
    "agriculture": ("农作物", "农业", "种植", "栽培", "水稻", "稻作", "粟", "黍"),
    "housing": ("房屋", "住房", "建筑", "居住", "干栏", "半地穴"),
    "fire": ("用火", "取火", "火"),
    "water_system": ("水利", "水利系统"),
}
GENERIC_TERMS = {
    "什么",
    "哪些",
    "怎样",
    "怎么",
    "如何",
    "为什么",
    "是否",
    "能否",
    "能不能",
    "主要",
    "方面",
    "有什么",
    "有何",
    "不同",
    "区别",
    "比较",
    "分别",
    "说明",
    "反映",
    "表明",
    "确定",
    "已经",
    "了吗",
}


@dataclass
class SupportAssessment:
    status: str
    reason_codes: list[str]
    required_facets: list[str]
    covered_facets: list[str]
    supporting_source_ids: list[str]
    supporting_knowledge_ids: list[str]
    unsupported_facets: list[str]
    method: str = METHOD
    calibration_version: str = CALIBRATION_VERSION
    facet_knowledge_ids: dict[str, set[str]] = field(default_factory=dict, repr=False)

    def public(self) -> dict:
        return {
            "status": self.status,
            "reason_codes": self.reason_codes,
            "required_facets": self.required_facets,
            "covered_facets": self.covered_facets,
            "supporting_source_ids": self.supporting_source_ids,
            "supporting_knowledge_ids": self.supporting_knowledge_ids,
            "unsupported_facets": self.unsupported_facets,
            "method": self.method,
            "calibration_version": self.calibration_version,
        }


def _lists(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _knowledge_ids(item: dict) -> list[str]:
    return _lists(item.get("knowledge_ids")) or _lists(item.get("knowledge_id"))


def _source_ids(item: dict) -> list[str]:
    return [
        str(reference.get("source_id") or "").strip()
        for reference in item.get("source_refs") or []
        if isinstance(reference, dict) and str(reference.get("source_id") or "").strip()
    ]


def _point_text(point: dict) -> str:
    values = [
        point.get("title"),
        point.get("summary"),
        point.get("time"),
    ]
    values.extend(_lists(point.get("people")))
    values.extend(_lists(point.get("keywords")))
    dimensions = point.get("dimensions") or {}
    if isinstance(dimensions, dict):
        values.extend(dimensions.values())
    return " ".join(str(value or "") for value in values)


def _subject_terms(point: dict) -> list[str]:
    terms = [str(point.get("title") or "")]
    terms.extend(_lists(point.get("people")))
    normalized = []
    for term in terms:
        term = term.strip()
        if len(term) >= 2 and term not in GENERIC_TERMS and term not in normalized:
            normalized.append(term)
    return normalized


def _catalog_terms(point: dict) -> list[str]:
    return list(dict.fromkeys(_subject_terms(point) + _lists(point.get("keywords"))))


def _term_aliases(term: str) -> list[str]:
    aliases = [term]
    stem = re.sub(r"(?:古城遗址|古城|遗址|先民|居民|文化|人)$", "", term)
    if len(stem) >= 2 and stem not in aliases:
        aliases.append(stem)
    return aliases


def _question_subjects(question: str, points: list[dict]) -> list[str]:
    matches = []
    for point in points:
        for term in _subject_terms(point):
            aliases = _term_aliases(term)
            direct_matches = [alias for alias in aliases if alias in question]
            if direct_matches:
                matches.append(max(direct_matches, key=len))
    matches = list(dict.fromkeys(matches))
    return [
        term
        for term in matches
        if not any(term != other and term in other for other in matches)
    ]


def _required_aspects(question: str) -> list[str]:
    aspects = [
        aspect
        for aspect, cues in ASPECT_CUES.items()
        if any(cue in question for cue in cues)
    ]
    if not aspects:
        aspects.append("content")
    return aspects


def _requested_topics(question: str) -> dict[str, tuple[str, ...]]:
    return {
        f"topic:{name}": aliases
        for name, aliases in TOPIC_GROUPS.items()
        if any(alias in question for alias in aliases)
    }


def _point_supports_aspect(point: dict, aspect: str) -> bool:
    dimensions = point.get("dimensions") or {}
    if not isinstance(dimensions, dict):
        dimensions = {}
    text = _point_text(point)
    if aspect == "content":
        return bool(str(point.get("summary") or "").strip())
    if aspect == "time":
        return bool(str(point.get("time") or "").strip()) or bool(
            re.search(r"(?:距今|公元|年前|世纪|年)", text)
        )
    if aspect == "place":
        return any(cue in text for cue in ("位于", "分布", "发现于", "地区", "流域"))
    if aspect == "reason":
        return bool(str(dimensions.get("reason") or "").strip()) or "原因" in text
    if aspect == "process":
        return bool(
            str(dimensions.get("process") or dimensions.get("content") or "").strip()
        )
    if aspect == "result_impact":
        return any(
            str(dimensions.get(key) or "").strip()
            for key in ("result", "impact", "significance")
        ) or any(cue in text for cue in ("促进", "推动", "改善", "奠定", "说明", "反映", "表明"))
    if aspect == "certainty":
        return bool(str(point.get("certainty") or "").strip())
    return False


def _point_matches_subject(point: dict, subject: str) -> bool:
    text = " ".join(_subject_terms(point))
    return any(alias in text for alias in _term_aliases(subject))


def _candidate_points(item: dict, point_map: dict[str, dict]) -> list[dict]:
    return [point_map[value] for value in _knowledge_ids(item) if value in point_map]


def _item_evidence_text(item: dict) -> str:
    return " ".join(
        str(reference.get("excerpt") or "")
        for reference in item.get("source_refs") or []
        if isinstance(reference, dict)
    )


def assess_support(
    question: str,
    retrieval_mode: str,
    candidates: list[dict],
    textbook_points: list[dict],
) -> SupportAssessment:
    """Assess whether linked textbook points cover the question's minimum facets."""
    del retrieval_mode  # Deliberately not used as a sufficiency shortcut.
    point_map = {
        str(point.get("knowledge_id") or ""): point
        for point in textbook_points
        if str(point.get("knowledge_id") or "")
    }
    subjects = _question_subjects(question, textbook_points)
    aspects = _required_aspects(question)
    topics = _requested_topics(question)
    is_comparison = any(cue in question for cue in COMPARISON_CUES) and len(subjects) >= 2
    required = [f"subject:{subject}" for subject in subjects]
    required.extend(f"aspect:{aspect}" for aspect in aspects)
    required.extend(topics)
    if is_comparison:
        required.append("comparison:all_subjects")

    facet_ids: dict[str, set[str]] = {facet: set() for facet in required}
    source_support: dict[str, set[str]] = {}
    for item in candidates:
        points = _candidate_points(item, point_map)
        evidence_text = _item_evidence_text(item)
        eligible_ids = set()
        for point in points:
            knowledge_id = str(point.get("knowledge_id") or "")
            matched_subjects = [
                subject for subject in subjects if _point_matches_subject(point, subject)
            ]
            aspects_match = all(
                _point_supports_aspect(point, aspect) for aspect in aspects
            )
            topics_match = all(
                any(alias in _point_text(point) for alias in aliases)
                and any(alias in evidence_text for alias in aliases)
                for aliases in topics.values()
            )
            if aspects_match and topics_match and (matched_subjects or not subjects):
                eligible_ids.add(knowledge_id)
                for subject in matched_subjects:
                    facet_ids[f"subject:{subject}"].add(knowledge_id)
                for aspect in aspects:
                    facet_ids[f"aspect:{aspect}"].add(knowledge_id)
                for topic in topics:
                    facet_ids[topic].add(knowledge_id)

        if eligible_ids:
            for source_id in _source_ids(item):
                source_support.setdefault(source_id, set()).update(eligible_ids)

    if not subjects:
        catalog_terms = [
            term
            for point in textbook_points
            for term in _catalog_terms(point)
            if any(alias in question for alias in _term_aliases(term))
        ]
        if not catalog_terms:
            required.insert(0, "subject:textbook_topic")
            facet_ids["subject:textbook_topic"] = set()
            source_support.clear()
            for aspect in aspects:
                facet_ids[f"aspect:{aspect}"].clear()
            for topic in topics:
                facet_ids[topic].clear()
        else:
            ids = {
                str(point.get("knowledge_id") or "")
                for point in textbook_points
                if any(term in _catalog_terms(point) for term in catalog_terms)
            }
            required.insert(0, "subject:textbook_topic")
            facet_ids["subject:textbook_topic"] = ids & {
                value for values in source_support.values() for value in values
            }

    if is_comparison:
        subject_facets = [facet for facet in required if facet.startswith("subject:")]
        if all(facet_ids.get(facet) for facet in subject_facets):
            facet_ids["comparison:all_subjects"] = set().union(
                *(facet_ids[facet] for facet in subject_facets)
            )

    covered = [facet for facet in required if facet_ids.get(facet)]
    unsupported = [facet for facet in required if not facet_ids.get(facet)]
    if not candidates:
        status = "insufficient"
        reasons = ["no_candidates"]
    elif not unsupported:
        status = "sufficient"
        reasons = ["all_required_facets_covered"]
    elif covered:
        status = "partial"
        reasons = ["required_facets_missing"]
    else:
        status = "insufficient"
        reasons = ["no_supported_facets"]

    supporting_ids = {value for values in source_support.values() for value in values}
    return SupportAssessment(
        status=status,
        reason_codes=reasons,
        required_facets=required,
        covered_facets=covered,
        supporting_source_ids=list(source_support),
        supporting_knowledge_ids=sorted(supporting_ids),
        unsupported_facets=unsupported,
        facet_knowledge_ids=facet_ids,
    )


def evidence_covers_assessment(
    assessment: SupportAssessment, used_evidence: list[dict]
) -> bool:
    """Require the actually used evidence to cover every required facet."""
    if assessment.status != "sufficient" or not used_evidence:
        return False
    used_ids = {
        str(knowledge_id)
        for evidence in used_evidence
        for knowledge_id in evidence.get("knowledge_ids") or []
        if knowledge_id
    }
    return all(
        bool(used_ids & assessment.facet_knowledge_ids.get(facet, set()))
        for facet in assessment.required_facets
    )


def supporting_answer_items(
    candidates: list[dict], assessment: SupportAssessment
) -> list[dict]:
    """Keep candidates intact externally while feeding only supporting excerpts inward."""
    source_ids = set(assessment.supporting_source_ids)
    knowledge_ids = set(assessment.supporting_knowledge_ids)
    selected = []
    for item in candidates:
        references = [
            reference
            for reference in item.get("source_refs") or []
            if isinstance(reference, dict) and reference.get("source_id") in source_ids
        ]
        if not references or not (set(_knowledge_ids(item)) & knowledge_ids):
            continue
        copy = dict(item)
        copy["source_refs"] = references
        excerpt_text = "\n".join(
            str(reference.get("excerpt") or "").strip()
            for reference in references
            if str(reference.get("excerpt") or "").strip()
        )
        copy["event"] = excerpt_text
        copy["content"] = excerpt_text
        copy["reason"] = ""
        copy["impact"] = ""
        selected.append(copy)
    return selected
