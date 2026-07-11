import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# 加载项目根目录下的 .env 文件，便于本地开发时配置数据库连接
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

# MySQL 数据库连接配置从环境变量读取，避免把本地账号密码写死在代码中
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:password@localhost:3306/history_ai?charset=utf8mb4",
)

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

# 创建数据库会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# SQLAlchemy 模型基类
Base = declarative_base()


def get_db():
    """FastAPI 依赖项：获取数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
