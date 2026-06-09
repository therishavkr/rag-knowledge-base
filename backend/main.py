from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel
from groq_service import get_llm
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.documents import Document
from fastapi import File, UploadFile
from document_processor import process_pdf
from vector_store import add_chunks_to_db, search_chunks, list_collections, delete_collection, filename_to_collection
from rag_pipeline import ask_question, search_only
from config import API_VERSION
from course_db import db as course_db
from grade_card_parser import parse_grade_card, generate_suggested_questions, StudentProfile
from recommender import get_recommendations, PreferencesForm
import os
import re

load_dotenv()


app = FastAPI(title="RAG Knowledge Base API", root_path=f"/api/{API_VERSION}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Load course data and index course descriptions into ChromaDB on first run."""
    course_db.load_all_data()

    existing = list_collections()
    if "courses" not in existing:
        print("Indexing course descriptions into ChromaDB (first run — this takes ~30s)…")
        chunks = _build_course_chunks()
        if chunks:
            add_chunks_to_db(chunks, "courses")
            print(f"Indexed {len(chunks)} course description chunks.")
    else:
        print("ChromaDB 'courses' collection already exists — skipping re-index.")


def _build_course_chunks() -> list[Document]:
    """Parse course_desc.txt and return LangChain Document chunks for ChromaDB."""
    data_path = os.path.join(os.path.dirname(__file__), "data", "course_desc.txt")
    if not os.path.exists(data_path):
        return []

    with open(data_path, encoding="utf-8", errors="replace") as f:
        text = f.read()

    blocks = re.split(r'(?=Course No:\s*[A-Z0-9*]+)', text)
    chunks: list[Document] = []
    for block in blocks:
        no_m = re.search(r'Course No:\s*([A-Z0-9*]+)', block)
        if not no_m:
            continue
        course_no = no_m.group(1).strip().rstrip('*')
        name_m = re.search(r'Course Name:\s*(.+)', block)
        desc_m = re.search(r'Description:\n(.*?)\nCourse Content:', block, re.DOTALL)
        content_m = re.search(r'Course Content:\n(.*?)(?:\nText Books:|\Z)', block, re.DOTALL)

        name = name_m.group(1).strip() if name_m else ""
        desc = desc_m.group(1).strip() if desc_m else ""
        content = content_m.group(1).strip() if content_m else ""
        combined = f"{name}. {desc} {content}".strip()

        if len(combined) < 20 or combined == "- -":
            continue

        chunks.append(Document(
            page_content=combined[:2000],
            metadata={"course_no": course_no, "name": name, "source": "course_catalog"},
        ))
    return chunks


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
    selected_docs: list = []
    mode: str = "ai"  # "ai" or "search"


@app.post("/ask")
def ask(request: QuestionRequest):
    if not request.selected_docs:
        collections = list_collections()
    else:
        collections = request.selected_docs

    if request.mode == "search":
        result = search_only(request.question, collections)
    else:
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


# ── Course Planner endpoints ─────────────────────────────────────────────

@app.post("/grade-card")
async def upload_grade_card(file: UploadFile = File(...)):
    """Parse a student grade card PDF and return their profile + semester context."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    try:
        contents = await file.read()
        profile = parse_grade_card(contents)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse grade card: {str(e)}. Please ensure it is a valid IITM grade card PDF."
        )

    mandatory = course_db.get_mandatory_courses(
        profile.dept_code, profile.batch, profile.next_semester
    )
    occupied_slots = sorted({c["slot"] for c in mandatory if c["slot"]})
    credit_summary = course_db.get_credits_earned(
        [c.model_dump() for c in profile.courses_taken],
        profile.dept_code,
        profile.batch,
    )

    return {
        "profile": profile,
        "mandatory_courses": mandatory,
        "occupied_slots": occupied_slots,
        "credit_summary": credit_summary,
        "suggested_questions": generate_suggested_questions(profile),
    }


class PreferencesRequest(BaseModel):
    profile: StudentProfile
    interests: str = ""
    workload_preference: str = "medium"
    minor_target: str | None = None
    credit_budget: int = 64
    free_text: str = ""


@app.post("/preferences")
def get_course_recommendations(req: PreferencesRequest):
    """Run the full hybrid recommendation pipeline for the given student profile + preferences."""
    prefs = PreferencesForm(
        interests=req.interests,
        workload_preference=req.workload_preference,
        minor_target=req.minor_target,
        credit_budget=req.credit_budget,
        free_text=req.free_text,
    )
    try:
        result = get_recommendations(req.profile, prefs, course_db)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Recommendation engine failed: {str(e)}. Try adjusting your preferences or credit budget."
        )
    return result


class ChatRecommendRequest(BaseModel):
    message: str
    profile: StudentProfile
    previous_preferences: PreferencesForm
    chat_history: list = []


@app.post("/chat-recommend")
def chat_recommend(req: ChatRecommendRequest):
    """
    Follow-up chat for refining recommendations.
    If the message contains filter intent (slot/credit/type keywords), re-runs recommendations
    with adjusted preferences and returns updated results alongside a conversational reply.
    """
    llm = get_llm()

    # Detect filter intent
    filter_keywords = re.compile(
        r'\b(slot|credit|hour|9\s*credit|12\s*credit|only|filter|show|management|'
        r'humanities|computing|light|heavy|medium|workload)\b',
        re.IGNORECASE,
    )
    has_filter_intent = bool(filter_keywords.search(req.message))

    updated_recs = None
    if has_filter_intent:
        # Merge the user's new request into preferences
        merged_prefs = PreferencesForm(
            interests=req.previous_preferences.interests,
            workload_preference=req.previous_preferences.workload_preference,
            minor_target=req.previous_preferences.minor_target,
            credit_budget=req.previous_preferences.credit_budget,
            free_text=req.message,   # append latest message as extra context
        )
        # Detect workload override
        if re.search(r'\b(light|easy|fewer)\b', req.message, re.IGNORECASE):
            merged_prefs.workload_preference = "light"
        elif re.search(r'\b(heavy|advanced|intensive)\b', req.message, re.IGNORECASE):
            merged_prefs.workload_preference = "heavy"

        updated_recs = get_recommendations(req.profile, merged_prefs, course_db)

    # Build a conversational reply via Groq
    system = (
        "You are a helpful academic advisor for IIT Madras students. "
        "Be concise (2-3 sentences). If courses were updated, briefly confirm what changed."
    )
    context = f"Student: {req.profile.dept_code}, Semester {req.profile.next_semester}, CGPA {req.profile.cgpa}."
    if updated_recs and updated_recs.recommended_electives:
        course_list = ", ".join(
            f"{c.course_name} ({c.slot})" for c in updated_recs.recommended_electives
        )
        context += f" Updated top recommendations: {course_list}."

    try:
        response = llm.invoke([
            SystemMessage(content=system),
            HumanMessage(content=f"{context}\n\nStudent said: {req.message}"),
        ])
        reply = response.content
    except Exception:
        reply = "I've updated the recommendations based on your request."

    return {
        "reply": reply,
        "updated_recommendations": updated_recs,
    }


@app.get("/minors")
def list_minors():
    """Return the list of available minor streams."""
    return {"minors": course_db.list_minors()}
