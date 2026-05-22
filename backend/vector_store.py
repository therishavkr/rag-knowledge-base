import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from langchain_core.documents import Document
import uuid
import re

embedding_fn = DefaultEmbeddingFunction()

client = chromadb.PersistentClient(path="./chroma_db")

def filename_to_collection(filename: str) -> str:
    # ChromaDB collection names can't have spaces or special chars
    name = re.sub(r'[^a-zA-Z0-9_-]', '_', filename)
    return f"doc_{name}"

def add_chunks_to_db(chunks: list, collection_name: str) -> int:
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_fn
    )

    documents = []
    metadatas = []
    ids = []

    for chunk in chunks:
        documents.append(chunk.page_content)
        metadatas.append(chunk.metadata)
        ids.append(str(uuid.uuid4()))

    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )

    return len(documents)

def search_chunks(query: str, collection_names: list, n_results: int = 5) -> list:
    all_docs = []

    for name in collection_names:
        try:
            collection = client.get_collection(
                name=name,
                embedding_function=embedding_fn
            )
            results = collection.query(
                query_texts=[query],
                n_results=n_results
            )
            for i, doc in enumerate(results["documents"][0]):
                all_docs.append(Document(
                    page_content=doc,
                    metadata=results["metadatas"][0][i]
                ))
        except Exception:
            continue  # skip if collection doesn't exist

    return all_docs

def list_collections() -> list:
    return [c.name for c in client.list_collections()]

def delete_collection(collection_name: str):
    client.delete_collection(collection_name)