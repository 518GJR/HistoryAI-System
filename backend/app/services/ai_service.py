def generate_answer(question: str, knowledge_items: list[dict]) -> str:
    """根据检索到的历史知识生成回答。

    当前版本不调用外部大模型，先将 RAG 检索结果整理成适合中小学学习的回答。
    """
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

        # 将命中的知识点按“事件、原因、影响”整理，符合中小学历史学习习惯
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
