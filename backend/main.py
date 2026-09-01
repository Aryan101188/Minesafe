import urllib.parse
import urllib.request
import json
from pathlib import Path
from datetime import datetime, timezone

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


# ============================================================
# RECYCLE BIN
# ============================================================

TRASH_DIR = Path("../data/trash")
TRASH_MANIFEST = TRASH_DIR / "manifest.json"


def load_trash_manifest():
    TRASH_DIR.mkdir(parents=True, exist_ok=True)

    if not TRASH_MANIFEST.exists():
        return {}

    try:
        data = json.loads(TRASH_MANIFEST.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_trash_manifest(manifest):
    TRASH_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = TRASH_DIR / "manifest.tmp"

    temp_path.write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8"
    )

    temp_path.replace(TRASH_MANIFEST)


def trashed_document_ids():
    return {
        int(document_id)
        for document_id in load_trash_manifest().keys()
        if str(document_id).isdigit()
    }


def document_is_trashed(document_id):
    return document_id in trashed_document_ids()




app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
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
    trash_ids = trashed_document_ids()

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

        return [
            dict(row._mapping)
            for row in result
            if row.id not in trash_ids
        ]


@app.get("/api/trash")
def get_trash():
    manifest = load_trash_manifest()

    if not manifest:
        return []

    document_ids = [int(value) for value in manifest.keys()]

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
                WHERE id IN :document_ids
                ORDER BY id DESC
            """).bindparams(
                __import__("sqlalchemy").bindparam(
                    "document_ids",
                    expanding=True
                )
            ),
            {"document_ids": document_ids}
        )

        documents = {
            row.id: dict(row._mapping)
            for row in result
        }

    trash = []

    for document_id, deleted in manifest.items():
        numeric_id = int(document_id)
        document = documents.get(numeric_id)

        if document is None:
            continue

        trash.append({
            **document,
            "deleted_at": deleted.get("deleted_at"),
        })

    return trash


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

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file selected."
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF documents are supported."
        )

    upload_dir = Path("/tmp/minesafe_uploads")
    upload_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    safe_filename = Path(file.filename).name
    file_path = upload_dir / safe_filename

    try:

        # Save uploaded file
        file_data = await file.read()

        with open(file_path, "wb") as buffer:
            buffer.write(file_data)

        print("UPLOAD FILE SAVED:", file_path)
        print("FILE SIZE:", len(file_data))

        # Process PDF + save DB
        document_id = save_document(
            str(file_path),
            safe_filename,
            safe_filename,
            "uploaded"
        )

        return {
            "message": "Document uploaded successfully",
            "filename": safe_filename,
            "document_id": document_id
        }

    except Exception as e:

        print("================================")
        print("UPLOAD ENDPOINT ERROR")
        print("ERROR:", repr(e))
        print("================================")

        raise HTTPException(
            status_code=500,
            detail=f"Upload processing failed: {str(e)}"
        )

    finally:

        try:
            if file_path.exists():
                file_path.unlink()
        except Exception:
            pass

# ============================================================
# DOCUMENT DELETE
# ============================================================

@app.delete("/api/documents/{document_id}")
def delete_document(document_id: int):
    """
    Move a document to MineSafe's recycle bin.

    Nothing is removed from the database or from the uploads directory.
    This makes accidental deletion reversible.
    """
    with engine.connect() as connection:
        document = connection.execute(
            text("""
                SELECT
                    id,
                    filename,
                    title,
                    document_type,
                    uploaded_at
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

    manifest = load_trash_manifest()

    if str(document_id) in manifest:
        return {
            "message": "Document is already in the recycle bin.",
            "document_id": document_id
        }

    manifest[str(document_id)] = {
        "deleted_at": datetime.now(timezone.utc).isoformat()
    }

    save_trash_manifest(manifest)

    return {
        "message": "Document moved to recycle bin.",
        "document_id": document_id
    }


@app.post("/api/trash/{document_id}/restore")
def restore_document(document_id: int):
    manifest = load_trash_manifest()

    if str(document_id) not in manifest:
        raise HTTPException(
            status_code=404,
            detail="Document is not in the recycle bin."
        )

    with engine.connect() as connection:
        document_exists = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM documents
                WHERE id = :document_id
            """),
            {"document_id": document_id}
        ).scalar()

    if not document_exists:
        raise HTTPException(
            status_code=404,
            detail="Original document record no longer exists."
        )

    del manifest[str(document_id)]
    save_trash_manifest(manifest)

    return {
        "message": "Document restored successfully.",
        "document_id": document_id
    }


@app.delete("/api/trash/{document_id}")
def permanently_delete_document(document_id: int):
    manifest = load_trash_manifest()

    if str(document_id) not in manifest:
        raise HTTPException(
            status_code=404,
            detail="Document is not in the recycle bin."
        )

    with engine.begin() as connection:
        document = connection.execute(
            text("""
                SELECT filename
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

    del manifest[str(document_id)]
    save_trash_manifest(manifest)

    # Only remove the physical PDF if no database record uses it anymore.
    if remaining == 0:
        upload_path = Path("../data/uploads") / Path(filename).name
        try:
            if upload_path.exists():
                upload_path.unlink()
        except OSError:
            pass

    return {
        "message": "Document permanently deleted.",
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
    if document_is_trashed(data.document_id):
        return {
            "result": "ERROR",
            "message": "This document is in the recycle bin. Restore it before running compliance checks."
        }

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
    results = search_tfidf(query, top_k=10)
    trash_ids = trashed_document_ids()

    return [
        result
        for result in results
        if result.get("document_id") not in trash_ids
    ][:5]


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
    trash_ids = trashed_document_ids()

    with engine.connect() as connection:
        document_rows = connection.execute(
            text("SELECT id FROM documents")
        ).fetchall()

        chunk_rows = connection.execute(
            text("SELECT document_id FROM chunks")
        ).fetchall()

        compliance_rows = connection.execute(
            text("SELECT document_id FROM compliance_checks")
        ).fetchall()

    document_count = sum(
        1 for row in document_rows
        if row.id not in trash_ids
    )

    chunk_count = sum(
        1 for row in chunk_rows
        if row.document_id not in trash_ids
    )

    compliance_count = sum(
        1 for row in compliance_rows
        if row.document_id not in trash_ids
    )

    return {
        "documents": document_count,
        "chunks": chunk_count,
        "compliance_checks": compliance_count
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
