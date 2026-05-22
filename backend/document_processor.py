from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import tempfile
import os

def process_pdf(file_bytes: bytes, filename: str) -> list:
    # Save uploaded file temporarily to disk
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    # Load the PDF
    loader = PyPDFLoader(tmp_path)
    documents = loader.load()

    # Split into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,      # each chunk = ~1000 characters
        chunk_overlap=200,    # chunks overlap by 200 chars so context isn't lost
    )
    chunks = splitter.split_documents(documents)

    # Cleanup temp file
    os.unlink(tmp_path)

    # Add filename metadata to each chunk
    for chunk in chunks:
        chunk.metadata["source"] = filename

    return chunks