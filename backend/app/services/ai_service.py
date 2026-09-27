"""RAG answer generation with an external-model fallback strategy."""

import json
import logging

import httpx

from app.services.provider_config import provider_config


logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一名面向中小学生的历史学习助手。
只能依据用户消息中提供的检索资料回答，不得编造资料中没有的史实。
回答应直接回应问题，并尽量从时间、人物、事件、原因、经过、结果或影响等角度清晰组织。
资料不足时要明确说明不足。引用资料时可使用[1]、[2]这样的来源编号。"""


def template_answer(question: str, knowledge_items: list[dict]) -> str:
    """根据检索到的历史知识生成回答，作为未配置模型或模型调用失败时的 fallback。"""
    if not knowledge_items:
        return (
            f"你提出的问题是：{question}。"
            "当前知识库中暂时没有匹配到相关历史知识点，建议换一个更具体的关键词，"
            "例如历史人物、朝代、事件名称等。"
        )

    answer_parts = [
        f"你提出的问题是：{question}",
        "根据当前历史知识库，找到以下相关内容：",
    ]

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

        answer_parts.append(
            f"{index}. {title}（{dynasty}，{time}）\n"
            f"事件：{event}\n"
            f"原因：{reason}\n"
            f"影响：{impact}\n"
            f"补充：{content}\n"
            f"匹配关键词：{matched_terms or '无'}；相关度分数：{score}。"
        )

    answer_parts.append("你可以继续追问某个事件的原因、影响或时间线。")
    return "\n".join(answer_parts)


def _create_client(timeout: float) -> httpx.Client:
    """为自动测试提供安装 httpx.MockTransport 的替换点。"""
    return httpx.Client(timeout=timeout)


def generate_answer_result(question: str, knowledge_items: list[dict]) -> tuple[str, str]:
    """返回回答和生成模式；模式为 ai 或 fallback。"""
    config = provider_config("AI")
    if not knowledge_items or not config:
        return template_answer(question, knowledge_items), "fallback"

    source_payload = [
        {"source_number": index, **item}
        for index, item in enumerate(knowledge_items, start=1)
    ]
    try:
        with _create_client(config["timeout"]) as client:
            response = client.post(
                f'{config["url"]}/chat/completions',
                headers={"Authorization": f'Bearer {config["key"]}'},
                json={
                    "model": config["model"],
                    "temperature": 0.2,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": json.dumps(
                                {"question": question, "sources": source_payload},
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
            return answer.strip(), "ai"
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
        logger.warning("AI request failed; using knowledge template: %s", exc)
        return template_answer(question, knowledge_items), "fallback"


def generate_answer(question: str, knowledge_items: list[dict]) -> str:
    """兼容原有调用方，仅返回回答文本。"""
    return generate_answer_result(question, knowledge_items)[0]
