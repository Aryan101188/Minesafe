import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


# Render provides DATABASE_URL through environment variables.
# For local development, it falls back to your local PostgreSQL database.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:YOUR_LOCAL_PASSWORD@127.0.0.1:5432/minesafe_db"
)

# Render may provide postgres://, which SQLAlchemy may not accept
# with newer versions, so convert it.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql+psycopg2://",
        1
    )

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()