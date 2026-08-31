import sys
import os

sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)
from sqlalchemy import text
from database import engine


def search_baseline(document_id, query):

    keywords = query.lower().split()

    with engine.connect() as connection:

        result = connection.execute(
            text("""
                SELECT
                    id,
                    page_number,
                    content
                FROM chunks
                WHERE document_id = :document_id
            """),
            {
                "document_id": document_id
            }
        )

        chunks = list(result)

    best_chunk = None
    best_score = 0

    for chunk in chunks:

        content = chunk.content.lower()

        score = 0

        print("Chunk:", chunk.id)
        print("Content:", chunk.content)

        for keyword in keywords:

            if keyword in content:
                score += 1

        if score > best_score:

            best_score = score
            best_chunk = chunk

    if best_chunk is None:
        return None

    return {
        "chunk_id": best_chunk.id,
        "page_number": best_chunk.page_number,
        "content": best_chunk.content,
        "score": best_score
    }
if __name__ == "__main__":

    result = search_baseline(
        1,
        "minimum required airflow"
    )

    print(result)