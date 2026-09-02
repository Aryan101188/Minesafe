from sqlalchemy import text
from database import engine

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import re


# ---------------------------------------------------------
# SEARCH SETTINGS
# ---------------------------------------------------------

MIN_RELEVANCE_SCORE = 0.50


# ---------------------------------------------------------
# WORD NORMALIZATION
# ---------------------------------------------------------

def normalize_query(query):

    query = query.lower()

    replacement = {
        "electrical": "electric",
        "electrically": "electric",
        "electrics": "electric",

        "ventilated": "ventilation",
        "ventilating": "ventilation",
        "ventilator": "ventilation",

        "speed": "velocity",

        "requirements": "requirement",
        "required": "requirement",
        "regulations": "regulation",
        "regulatory": "regulation",
        "explosives": "explosive",
    }

    words = query.split()

    return " ".join(
        replacement.get(word, word)
        for word in words
    )


def normalize_text(text):

    text = text.lower()

    replacements = {
        "electrical": "electric",
        "electrically": "electric",
        "electrics": "electric",
        "requirements": "requirement",
        "required": "requirement",
        "regulations": "regulation",
        "regulatory": "regulation",
        "explosives": "explosive",
    }

    words = text.split()

    return " ".join(
        replacements.get(word, word)
        for word in words
    )


# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------

def get_all_chunks():

    with engine.connect() as connection:

        result = connection.execute(
            text("""
                SELECT
                    c.id,
                    c.document_id,
                    c.page_number,
                    c.content,
                    d.title AS document_title,
                    d.filename
                FROM chunks c
                JOIN documents d
                    ON c.document_id = d.id
                ORDER BY c.document_id, c.page_number, c.id
            """)
        )

        chunks = []

        for row in result:

            chunks.append({
                "chunk_id": row.id,
                "document_id": row.document_id,
                "page_number": row.page_number,
                "content": row.content,
                "document_title": row.document_title,
                "filename": row.filename
            })

        return chunks


# ---------------------------------------------------------
# TEXT PROCESSING
# ---------------------------------------------------------

def clean_pdf_text(text):

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


def split_regulatory_clauses(text):

    cleaned = clean_pdf_text(text)

    matches = list(
        re.finditer(
            r"\(\s*\d+\s*\)",
            cleaned
        )
    )

    if not matches:
        return []

    clauses = []

    for i, match in enumerate(matches):

        start = match.start()

        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(cleaned)

        clause = cleaned[start:end].strip()

        if len(clause) >= 20:
            clauses.append(clause)

    return clauses


def split_sentences(text):

    cleaned = clean_pdf_text(text)

    sentences = re.split(
        r"(?<=[.!?;])\s+",
        cleaned
    )

    return [
        sentence.strip()
        for sentence in sentences
        if len(sentence.strip()) >= 20
    ]


# ---------------------------------------------------------
# ANSWER EXTRACTION
# ---------------------------------------------------------

def get_best_sentence(query, content):

    cleaned = clean_pdf_text(content)

    # Prefer complete numbered regulatory clauses.
    clauses = split_regulatory_clauses(
        cleaned
    )

    if clauses:

        candidates = clauses

    else:

        candidates = split_sentences(
            cleaned
        )

    if not candidates:
        return cleaned

    normalized_query = normalize_query(
        query
    )

    normalized_candidates = [
        normalize_text(candidate)
        for candidate in candidates
    ]

    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english"
    )

    try:

        vectors = vectorizer.fit_transform(
            normalized_candidates + [
                normalized_query
            ]
        )

        scores = cosine_similarity(
            vectors[-1],
            vectors[:-1]
        )[0]

        best_index = scores.argmax()

        return candidates[best_index]

    except ValueError:

        return candidates[0]


# ---------------------------------------------------------
# SEARCH
# ---------------------------------------------------------

def search_tfidf(query, top_k=3):

    query = query.strip()

    if not query:
        return []

    chunks = get_all_chunks()

    if not chunks:
        return []

    normalized_query = normalize_query(
        query
    )

    documents = [
        normalize_text(
            chunk["content"]
        )
        for chunk in chunks
    ]

    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english"
    )

    try:

        chunk_vectors = vectorizer.fit_transform(
            documents
        )

        query_vector = vectorizer.transform(
            [normalized_query]
        )

        scores = cosine_similarity(
            query_vector,
            chunk_vectors
        )[0]

    except ValueError:

        return []

    results = []

    for i, score in enumerate(scores):

        # Ignore weak matches. This prevents unrelated
        # regulatory text from being presented as evidence.
        if score < MIN_RELEVANCE_SCORE:
            continue

        chunk = chunks[i]

        answer = get_best_sentence(
            query,
            chunk["content"]
        )

        results.append({

            "chunk_id": chunk["chunk_id"],

            "document_id": chunk["document_id"],

            "document_title": chunk["document_title"],

            "filename": chunk["filename"],

            "page_number": chunk["page_number"],

            "answer": answer,

            # Full original chunk is preserved for
            # supporting regulatory evidence.
            "content": chunk["content"],

            "score": float(score)

        })

    results.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    # Keep only the strongest result from each document.
    # This prevents multiple chunks from the same PDF from
    # filling the search results.
    unique_results = []
    seen_documents = set()

    for result in results:

        document_id = result["document_id"]

        if document_id in seen_documents:
            continue

        seen_documents.add(document_id)
        unique_results.append(result)

        if len(unique_results) >= top_k:
            break

    return unique_results


# ---------------------------------------------------------
# TEST
# ---------------------------------------------------------

if __name__ == "__main__":

    queries = [
        "electrical safety",
        "minimum required airflow",
        "explosives",
        "mine rescue",
        "ventilation",
        "safety lamps"
    ]

    for query in queries:

        print("\n================================")
        print("QUERY:", query)
        print("================================")

        results = search_tfidf(
            query,
            top_k=3
        )

        if not results:

            print(
                "No strongly matching regulatory "
                "evidence found."
            )

            continue

        for rank, result in enumerate(
            results,
            start=1
        ):

            print("\nRank:", rank)
            print(
                "Document:",
                result["document_title"]
            )
            print(
                "Page:",
                result["page_number"]
            )
            print(
                "Score:",
                round(result["score"], 3)
            )
            print(
                "Answer:",
                result["answer"]
            )
