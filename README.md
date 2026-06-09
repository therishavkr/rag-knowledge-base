# IITM Course Planner + RAG Knowledge Base

An AI-powered tool for IIT Madras students with two modes:

1. **Course Planner** — Upload your grade card, set preferences, and get a personalised semester plan with slot-conflict-free elective recommendations ranked by Groq's LLaMA 3.3 70B.
2. **Document Chat** — Upload any PDF and chat with it using Retrieval-Augmented Generation (RAG).

## Live Demo
- **App:** https://rag-knowledge-base-three.vercel.app
- **API Docs:** https://rag-knowledge-base-api.onrender.com/docs

> Backend is on Render's free tier — may take 30–60 s to wake up on first request.

---

## Course Planner

### How it works

1. **Upload grade card** — drag and drop your IITM linear grade card PDF. The parser extracts your roll number, department, batch, CGPA, and every course you've completed.
2. **Set preferences** — choose your interests (free text), preferred workload (Light / Medium / Heavy), a minor stream target, and credit budget.
3. **Get recommendations** — a three-stage hybrid pipeline runs:
   - **Stage 1 (hard rules):** removes courses in occupied slots, courses with unmet prerequisites, and courses that exceed your credit budget.
   - **Stage 2 (semantic search):** ChromaDB ranks remaining candidates against your interests using sentence embeddings.
   - **Stage 3 (LLM ranking):** Groq LLaMA 3.3 70B picks the top 5 and writes a one-sentence explanation for each.
4. **Build your schedule** — add electives to your semester grid. Slot conflicts are flagged live. Credit counter updates as you add courses.
5. **Refine with chat** — ask follow-up questions ("only show 9-credit courses", "avoid courses with exams") and the recommendations update instantly.

### Key features

- Upcoming semester auto-detected from roll number batch year + current date (not grade card term count — immune to summer course inflation)
- Slot conflict detection: mandatory course slots are occupied automatically; elective slots checked against the full slotwise catalog
- Prerequisite parsing: handles free-text like `"CS1200 and CS2700"`, `"Nil"`, `"COT"`, `"CE2060 or equivalent"`
- Credit tracker: per-category progress (Engineering, Computing, Humanities, Sciences, Management, …) vs. program requirements
- Minor stream progress: shows completed vs. remaining courses for your chosen minor
- 3,624 course descriptions indexed in ChromaDB at startup for semantic search
- `localStorage` persistence for your selected electives across page refreshes

### Data sources (`backend/data/`)

| File | Contents |
|------|----------|
| `slotwise_details_cleaned.csv` | ~3,300 electives with slot, credits, prerequisites, BTech/DD eligibility |
| `sem_wise_details.csv` | Mandatory courses per department / batch / semester |
| `master_course_catalog_final.csv` | Master catalog with slot info for mandatory course lookup |
| `credit_requirement.csv` | Per-department credit targets by category |
| `course_desc.txt` | Full course descriptions (indexed into ChromaDB) |
| `minor.txt` | 21+ minor streams with course lists |
| `course_type.csv` | Category code to human-readable name |

---

## Document Chat

Upload PDFs and get accurate answers with source citations, powered by LLaMA 3.3 70B and ChromaDB vector search.

- Upload multiple PDFs to your knowledge base
- Semantic vector search using ChromaDB
- Conversation memory for follow-up questions
- Source citations on every answer
- Query specific documents or all at once
- Delete documents from the knowledge base

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Groq (LLaMA 3.3 70B) |
| RAG / chains | LangChain |
| Vector database | ChromaDB |
| Embeddings | all-MiniLM-L6-v2 (ChromaDB default) |
| PDF parsing | pdfplumber (grade card), PyPDF (documents) |
| Data processing | pandas |
| Backend | FastAPI (Python 3.11+) |
| Frontend | React + Vite |
| Deployment | Render + Vercel |

---

## Project Structure

```
rag-knowledge-base/
├── backend/
│   ├── main.py                    # FastAPI server, all endpoints, startup indexing
│   ├── course_db.py               # CourseDB singleton — loads all CSVs, query helpers
│   ├── grade_card_parser.py       # pdfplumber-based IITM grade card parser
│   ├── recommender.py             # 3-stage hybrid recommendation pipeline
│   ├── rag_pipeline.py            # Document RAG logic with conversation memory
│   ├── vector_store.py            # ChromaDB add / search / list / delete
│   ├── document_processor.py      # PDF chunking for document chat
│   ├── groq_service.py            # Groq LLM setup (LLaMA 3.3 70B)
│   ├── config.py                  # API version config
│   ├── requirements.txt
│   └── data/
│       ├── slotwise_details_cleaned.csv
│       ├── sem_wise_details.csv
│       ├── master_course_catalog_final.csv
│       ├── credit_requirement.csv
│       ├── course_desc.txt
│       ├── minor.txt
│       └── course_type.csv
└── frontend/
    └── src/
        ├── App.jsx                # Tab switcher, shared state, localStorage
        ├── config.js              # API base URL
        ├── index.css
        └── components/
            ├── GradeCardUpload.jsx    # PDF drag-and-drop upload
            ├── PreferencesForm.jsx    # Interests, workload, minor, credit budget
            ├── RecommendationPanel.jsx # Top-5 cards + Also Consider + minor progress
            ├── SemesterGrid.jsx       # Slot grid with conflict detection
            ├── CreditTracker.jsx      # Per-category credit progress table
            ├── ChatRefine.jsx         # Follow-up chat for refining recommendations
            ├── Upload.jsx             # Document chat PDF upload
            └── Chat.jsx               # Document chat interface
```

---

## Run Locally

### Prerequisites
- Python 3.11+
- Node.js 18+
- Groq API key — free at [console.groq.com](https://console.groq.com)

### Backend

```bash
cd backend
pip install -r requirements.txt

# Create .env
echo "GROQ_API_KEY=your_key_here" > .env

# Start server (first run indexes course descriptions into ChromaDB — takes ~30 s)
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install

# Create .env.development
echo "VITE_API_URL=http://localhost:8000" > .env.development

npm run dev
```

Open **http://localhost:5173**

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/grade-card` | Upload grade card PDF → returns profile + mandatory courses + credit summary |
| `POST` | `/api/v1/preferences` | Student profile + preferences → 3-stage recommendation result |
| `POST` | `/api/v1/chat-recommend` | Follow-up chat — re-runs recommendations if filter intent detected |
| `GET`  | `/api/v1/minors` | List of available minor streams |
| `POST` | `/api/v1/upload` | Upload PDF for document chat |
| `POST` | `/api/v1/ask` | Ask a question over uploaded documents |
| `GET`  | `/api/v1/documents` | List uploaded document collections |
| `DELETE` | `/api/v1/documents/{name}` | Delete a document collection |

---

## Environment Variables

**`backend/.env`**
```
GROQ_API_KEY=your_groq_api_key
```

**`frontend/.env.development`**
```
VITE_API_URL=http://localhost:8000
```

---

## Screenshots

![App Screenshot](screenshots/1.png)
