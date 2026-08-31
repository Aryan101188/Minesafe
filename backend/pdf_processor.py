from pypdf import PdfReader
from database import SessionLocal
from sqlalchemy import text


def extract_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)

    pages = []

    for page in reader.pages:
        text_content = page.extract_text()

        if text_content:
            pages.append(text_content)

    return pages


def save_document(pdf_path, filename, title, document_type):
    pages = extract_text_from_pdf(pdf_path)

    db = SessionLocal()

    try:
        # Insert document
        result = db.execute(
            text("""
                INSERT INTO documents (filename, title, document_type)
                VALUES (:filename, :title, :document_type)
                RETURNING id
            """),
            {
                "filename": filename,
                "title": title,
                "document_type": document_type
            }
        )

        document_id = result.scalar()

        # Insert chunks
        for page_number, content in enumerate(pages, start=1):
            db.execute(
                text("""
                    INSERT INTO chunks
                    (document_id, page_number, content)
                    VALUES (:document_id, :page_number, :content)
                """),
                {
                    "document_id": document_id,
                    "page_number": page_number,
                    "content": content
                }
            )

        db.commit()

        print("DOCUMENT SAVED!")
        print("Document ID:", document_id)
        print("Number of pages:", len(pages))

    except Exception as e:
        db.rollback()
        print("ERROR:", e)

    finally:
        db.close()


if __name__ == "__main__":
    pdf_path = "../data/mine_ventilation_rules.pdf"

    save_document(
        pdf_path,
        "mine_ventilation_rules.pdf",
        "Mine Safety and Ventilation Regulations 2026",
        "regulation"
    )