import urllib.parse
import urllib.request
import json
from pathlib import Path

from sqlalchemy import text
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import engine
from pdf_processor import save_document
from incident_classifier import classify_incident
from priority_engine import calculate_priority
from compliance_engine import check_compliance
from retriever import find_ventilation_rule
from requirement_extractor import extract_airflow_requirement
from tfidf_retriever import search_tfidf


app = FastAPI(title="MineSafe API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "project": "MineSafe"
    }


# ============================================================
# DOCUMENTS
# ============================================================

@app.get("/api/documents")
def get_documents():
    with engine.connect() as connection:
        result = connection.execute(
            text("""
                SELECT
                    id,
                    filename,
                    title,
                    document_type,
                    uploaded_at
                FROM documents
                ORDER BY id
            """)
        )

        return [dict(row._mapping) for row in result]


@app.get("/api/documents/{document_id}/chunks")
def get_document_chunks(document_id: int):
    with engine.connect() as connection:
        result = connection.execute(
            text("""
                SELECT
                    id,
                    page_number,
                    content
                FROM chunks
                WHERE document_id = :document_id
                ORDER BY page_number, id
            """),
            {"document_id": document_id}
        )

        return [dict(row._mapping) for row in result]


# ============================================================
# DOCUMENT UPLOAD
# ============================================================

@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF documents are supported."
        )

    upload_dir = Path("../data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / Path(file.filename).name

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    save_document(
        str(file_path),
        file.filename,
        file.filename,
        "uploaded"
    )

    return {
        "message": "Document uploaded successfully",
        "filename": file.filename
    }


# ============================================================
# DOCUMENT DELETE
# ============================================================

@app.delete("/api/documents/{document_id}")
def delete_document(document_id: int):
    """
    Delete a document and all database records belonging to it.

    Order matters:
    1. compliance_checks
    2. chunks
    3. documents

    The physical PDF is removed only when no other document record
    uses the same filename.
    """
    with engine.begin() as connection:
        document = connection.execute(
            text("""
                SELECT id, filename
                FROM documents
                WHERE id = :document_id
            """),
            {"document_id": document_id}
        ).mappings().first()

        if document is None:
            raise HTTPException(
                status_code=404,
                detail="Document not found."
            )

        filename = document["filename"]

        connection.execute(
            text("""
                DELETE FROM compliance_checks
                WHERE document_id = :document_id
            """),
            {"document_id": document_id}
        )

        connection.execute(
            text("""
                DELETE FROM chunks
                WHERE document_id = :document_id
            """),
            {"document_id": document_id}
        )

        connection.execute(
            text("""
                DELETE FROM documents
                WHERE id = :document_id
            """),
            {"document_id": document_id}
        )

        remaining = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM documents
                WHERE filename = :filename
            """),
            {"filename": filename}
        ).scalar()

    # Do not remove a shared PDF if another database record still uses it.
    if remaining == 0:
        upload_path = Path("../data/uploads") / Path(filename).name
        try:
            if upload_path.exists():
                upload_path.unlink()
        except OSError:
            pass

    return {
        "message": "Document deleted successfully",
        "document_id": document_id
    }


# ============================================================
# COMPLIANCE
# ============================================================

class AirflowCheck(BaseModel):
    document_id: int
    actual_airflow: float


@app.post("/api/compliance/check")
def compliance_check(data: AirflowCheck):
    rule = find_ventilation_rule(data.document_id)

    if rule is None:
        return {
            "result": "ERROR",
            "message": "No regulatory requirement found for this document."
        }

    required_airflow = extract_airflow_requirement(rule["content"])

    if required_airflow is None:
        return {
            "result": "ERROR",
            "message": (
                "Could not extract a numeric requirement "
                "from the regulatory evidence."
            )
        }

    result = check_compliance(
        required_value=required_airflow,
        actual_value=data.actual_airflow,
        unit="m3/s"
    )

    with engine.begin() as connection:
        connection.execute(
            text("""
                INSERT INTO compliance_checks
                (
                    document_id,
                    rule_text,
                    actual_value,
                    required_value,
                    result,
                    severity,
                    evidence
                )
                VALUES
                (
                    :document_id,
                    :rule_text,
                    :actual_value,
                    :required_value,
                    :result,
                    :severity,
                    :evidence
                )
            """),
            {
                "document_id": data.document_id,
                "rule_text": rule["content"],
                "actual_value": f"{data.actual_airflow} m3/s",
                "required_value": f"{required_airflow} m3/s",
                "result": result["result"],
                "severity": result["severity"],
                "evidence": (
                    f"Page {rule['page_number']}: "
                    f"{rule['content']}"
                )
            }
        )

    return {
        "result": result["result"],
        "severity": result["severity"],
        "message": result["message"],
        "domain": "Ventilation Safety",
        "measurement": {
            "actual": data.actual_airflow,
            "required": required_airflow,
            "unit": "m3/s"
        },
        "evidence": {
            "chunk_id": rule["chunk_id"],
            "page_number": rule["page_number"],
            "text": rule["content"],
            "required_airflow": required_airflow
        }
    }


# ============================================================
# REGULATORY SEARCH
# ============================================================

@app.get("/api/search")
def search_documents(query: str):
    return search_tfidf(query, top_k=5)


# ============================================================
# EXTERNAL SEARCH
# ============================================================

@app.get("/api/external-search")
def external_search(query: str):
    if not query.strip():
        return []

    encoded_query = urllib.parse.quote(query)

    url = (
        "https://en.wikipedia.org/w/api.php"
        "?action=query"
        "&list=search"
        "&format=json"
        "&srlimit=3"
        f"&srsearch={encoded_query}"
    )

    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent":
                    "MineSafe/1.0 Engineering Compliance System"
            }
        )

        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(
                response.read().decode("utf-8")
            )

        results = []

        for item in data.get("query", {}).get("search", []):
            title = item.get("title", "")
            snippet = item.get("snippet", "")

            snippet = snippet.replace(
                '<span class="searchmatch">', ""
            )
            snippet = snippet.replace("</span>", "")

            results.append({
                "title": title,
                "snippet": snippet,
                "source": "Wikipedia",
                "url": (
                    "https://en.wikipedia.org/wiki/"
                    + urllib.parse.quote(title.replace(" ", "_"))
                )
            })

        return results

    except Exception as error:
        print("External search error:", repr(error))
        return {
            "error": "External search unavailable",
            "details": str(error)
        }


# ============================================================
# INCIDENT CLASSIFICATION
# ============================================================

class IncidentCheck(BaseModel):
    description: str


@app.post("/api/incidents/classify")
def classify_incident_api(data: IncidentCheck):
    category = classify_incident(data.description)

    priority = calculate_priority(
        data.description,
        category
    )

    return {
        "category": category,
        "priority": priority
    }


# ============================================================
# DASHBOARD STATISTICS
# ============================================================

@app.get("/api/stats")
def get_stats():
    with engine.connect() as connection:
        document_count = connection.execute(
            text("SELECT COUNT(*) FROM documents")
        ).scalar()

        chunk_count = connection.execute(
            text("SELECT COUNT(*) FROM chunks")
        ).scalar()

        compliance_count = connection.execute(
            text("SELECT COUNT(*) FROM compliance_checks")
        ).scalar()

    return {
        "documents": document_count,
        "chunks": chunk_count,
        "compliance_checks": compliance_count
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
