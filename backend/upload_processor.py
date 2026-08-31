from pypdf import PdfReader
from sqlalchemy import text

from database import engine
from chunker import create_chunks


PDF_PATH = "../data/mine_ventilation_rules.pdf"


def process_pdf():

    # 1. Read the PDF
    reader = PdfReader(PDF_PATH)

    # 2. Create a document record
    with engine.begin() as connection:

        result = connection.execute(
            text("""
                INSERT INTO documents
                    (filename, title, document_type)
                VALUES
                    (:filename, :title, :document_type)
                RETURNING id;
            """),
            {
                "filename": "mine_ventilation_rules.pdf",
                "title": "Mine Safety and Ventilation Regulations 2026",
                "document_type": "regulation"
            }
        )

        document_id = result.scalar()

        print("Created document with ID:", document_id)

        # 3. Process every PDF page
        for page_number, page in enumerate(reader.pages, start=1):

            page_text = page.extract_text()

            if not page_text:
                continue

            # 4. Split page text into chunks
            chunks = create_chunks(page_text, 300)

            # 5. Save every chunk
            for chunk in chunks:

                connection.execute(
                    text("""
                        INSERT INTO chunks
                            (document_id, page_number, content)
                        VALUES
                            (:document_id, :page_number, :content);
                    """),
                    {
                        "document_id": document_id,
                        "page_number": page_number,
                        "content": chunk
                    }
                )

                print(
                    f"Saved chunk from page {page_number}"
                )

    print("PDF processing completed!")


if __name__ == "__main__":
    process_pdf()