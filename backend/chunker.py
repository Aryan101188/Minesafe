def create_chunks(text, chunk_size=300):
    chunks = []

    start = 0

    while start < len(text):
        end = start + chunk_size

        chunk = text[start:end]

        chunks.append(chunk.strip())

        start = end

    return chunks
if __name__ == "__main__":
    sample_text = """
    All underground working areas shall have adequate ventilation.
    The ventilation system shall maintain the required airflow.
    Ventilation measurements shall be recorded during safety inspections.
    """

    chunks = create_chunks(sample_text, 100)

    print("Number of chunks:", len(chunks))

    for i, chunk in enumerate(chunks):
        print("\n--- CHUNK", i + 1, "---")
        print(chunk)