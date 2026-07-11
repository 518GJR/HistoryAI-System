from sqlalchemy import Column, DateTime, Integer, String, Text, func

from app.database import Base


class User(Base):
    """用户表模型，用于后续登录、问答记录归属等功能。"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, comment="用户ID")
    username = Column(String(50), unique=True, nullable=False, index=True, comment="用户名")
    password_hash = Column(String(255), nullable=False, comment="加密后的密码")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")


class HistoryKnowledge(Base):
    """历史知识表模型，用于存储知识点、朝代、关键词和知识内容。"""

    __tablename__ = "history_knowledge"

    id = Column(Integer, primary_key=True, index=True, comment="知识点ID")
    title = Column(String(100), nullable=False, index=True, comment="知识点标题")
    dynasty = Column(String(50), nullable=True, index=True, comment="所属朝代")
    keywords = Column(String(255), nullable=True, comment="关键词，使用逗号分隔")
    content = Column(Text, nullable=False, comment="知识点正文内容")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
