from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# DB 연결 URL (예: SQLite → Oracle, PostgreSQL, MySQL 등으로 변경 가능)
SQLALCHEMY_DATABASE_URL = "oracle+cx_oracle://admin:1234@localhost:1521/xe"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
