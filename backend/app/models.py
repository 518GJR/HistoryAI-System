from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.database import Base


class User(Base):
    """用户表模型，用于后续登录、问答记录归属等功能。"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, comment="用户ID")
    username = Column(String(50), unique=True, nullable=False, index=True, comment="用户名")
    password_hash = Column(String(255), nullable=False, comment="加密后的密码")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")


class HistoryKnowledge(Base):
    """历史知识表模型，用于存储结构化历史知识点。"""

    __tablename__ = "history_knowledge"

    id = Column(Integer, primary_key=True, index=True, comment="知识点ID")
    title = Column(String(100), nullable=False, unique=True, index=True, comment="知识点标题")
    dynasty = Column(String(50), nullable=True, index=True, comment="所属朝代或时期")
    time = Column(String(100), nullable=True, comment="历史时间")
    people = Column(Text, nullable=True, comment="相关人物，使用 JSON 字符串存储")
    event = Column(Text, nullable=True, comment="历史事件")
    reason = Column(Text, nullable=True, comment="事件原因")
    impact = Column(Text, nullable=True, comment="历史影响")
    keywords = Column(Text, nullable=True, comment="关键词，使用 JSON 字符串存储")
    content = Column(Text, nullable=False, comment="知识点正文内容")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )


class QuestionHistory(Base):
    """问答历史表模型，用于后续保存用户问题、回答和知识来源快照。"""

    __tablename__ = "question_history"

    id = Column(Integer, primary_key=True, index=True, comment="问答记录ID")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True, comment="用户ID")
    question = Column(Text, nullable=False, comment="用户问题")
    answer = Column(Text, nullable=False, comment="系统回答")
    sources = Column(Text, nullable=True, comment="知识来源快照，使用 JSON 字符串存储")
    created_at = Column(DateTime, server_default=func.now(), index=True, comment="创建时间")
