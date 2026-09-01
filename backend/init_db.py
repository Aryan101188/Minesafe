from sqlalchemy import text
from database import engine


CREATE_DOCUMENTS = """
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    title TEXT NOT NULL,
    document_type TEXT DEFAULT 'PDF',
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


CREATE_CHUNKS = """
CREATE TABLE IF NOT EXISTS chunks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    content TEXT NOT NULL
);
"""


CREATE_COMPLIANCE = """
CREATE TABLE IF NOT EXISTS compliance_checks (
    id SERIAL PRIMARY KEY,
    document_id INTEGER,
    rule_text TEXT,
    actual_value TEXT,
    required_value TEXT,
    result TEXT,
    severity TEXT,
    evidence TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


with engine.begin() as connection:
    connection.execute(text(CREATE_DOCUMENTS))
    connection.execute(text(CREATE_CHUNKS))
    connection.execute(text(CREATE_COMPLIANCE))

print("MineSafe database tables are ready.")