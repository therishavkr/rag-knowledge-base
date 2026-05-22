from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel
from groq_service import get_llm
from langchain_core.messages import HumanMessage
from fastapi import File, UploadFile
from document_processor import process_pdf
from vector_store import add_chunks_to_db, search_chunks, list_collections, delete_collection, filename_to_collection
from rag_pipeline import ask_question
import os

load_dotenv()

app = FastAPI(title="RAG Knowledge Base API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "RAG Knowledge Base is running 🚀"}

@app.get("/health")
def health():
    groq_key = os.getenv("GROQ_API_KEY")
    return {
        "status": "ok",
        "groq_key_loaded": bool(groq_key)
    }

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
def chat(request: ChatRequest):
    llm = get_llm()
    response = llm.invoke([HumanMessage(content=request.message)])
    return {"reply": response.content}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        return {"error": "Only PDF files are supported right now"}

    contents = await file.read()
    chunks = process_pdf(contents, file.filename)

    collection_name = filename_to_collection(file.filename)
    stored = add_chunks_to_db(chunks, collection_name)

    return {
        "filename": file.filename,
        "collection": collection_name,
        "chunks_stored": stored,
        "status": "ready to query! ✅"
    }



class QuestionRequest(BaseModel):
    question: str
    chat_history: list = []
    selected_docs: list = []  # empty = search all docs

@app.post("/ask")
def ask(request: QuestionRequest):
    if not request.selected_docs:
        collections = list_collections()
    else:
        collections = request.selected_docs  # already collection names, no conversion needed

    result = ask_question(request.question, request.chat_history, collections)
    return result

@app.get("/documents")
def get_documents():
    collections = list_collections()
    return {"documents": collections}

@app.delete("/documents/{collection_name}")
def remove_document(collection_name: str):
    delete_collection(collection_name)
    return {"status": f"{collection_name} deleted ✅"}