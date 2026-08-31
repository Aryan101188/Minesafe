from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker, declarative_base


DATABASE_URL = URL.create(
    drivername="postgresql+psycopg2",
    username="postgres",
    password="Aryan1234@",
    host="127.0.0.1",
    port=5432,
    database="minesafe_db"
)

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()