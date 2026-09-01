from pypdf import PdfReader
from database import SessionLocal
from sqlalchemy import text


def extract_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)

    pages = []

    for page in reader.pages:
        try:
            text_content = page.extract_text()
        except Exception as e:
            print("WARNING: Could not extract one page:", e)
            text_content = ""

        if text_content:
            pages.append(text_content)

    return pages


def save_document(pdf_path, filename, title, document_type):

    db = SessionLocal()

    try:
        # -----------------------------------------
        # Extract PDF text
        # -----------------------------------------
        pages = extract_text_from_pdf(pdf_path)

        print("PDF READ SUCCESSFULLY")
        print("Pages:", len(pages))

        # -----------------------------------------
        # Insert document
        # -----------------------------------------
        result = db.execute(
            text("""
                INSERT INTO documents
                (filename, title, document_type)
                VALUES
                (:filename, :title, :document_type)
                RETURNING id
            """),
            {
                "filename": filename,
                "title": title,
                "document_type": document_type
            }
        )

        document_id = result.scalar()

        # -----------------------------------------
        # Insert chunks
        # -----------------------------------------
        for page_number, content in enumerate(pages, start=1):

            db.execute(
                text("""
                    INSERT INTO chunks
                    (document_id, page_number, content)
                    VALUES
                    (:document_id, :page_number, :content)
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

        return document_id

    except Exception as e:

        db.rollback()

        print("================================")
        print("UPLOAD DATABASE/PDF ERROR")
        print("ERROR:", repr(e))
        print("================================")

        raise

    finally:
        db.close()