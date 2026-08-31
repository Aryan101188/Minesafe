from sqlalchemy import text
from database import engine


def find_ventilation_rule(document_id):

    with engine.connect() as connection:

        result = connection.execute(
            text("""
                SELECT
                    id,
                    page_number,
                    content
                FROM chunks
                WHERE document_id = :document_id
                AND LOWER(content) LIKE '%airflow%'
                AND (
                    LOWER(content) LIKE '%required%'
                    OR LOWER(content) LIKE '%minimum%'
                )
                ORDER BY
                    CASE
                        WHEN LOWER(content) LIKE '%m3/s%' THEN 0
                        ELSE 1
                    END,
                    page_number,
                    id
                LIMIT 1;
            """),
            {
                "document_id": document_id
            }
        )

        row = result.fetchone()

        if row is None:
            return None

        return {
            "chunk_id": row.id,
            "page_number": row.page_number,
            "content": row.content
        }


if __name__ == "__main__":
    rule = find_ventilation_rule(1)
    print(rule)