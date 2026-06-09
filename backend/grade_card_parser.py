import re
import datetime
import tempfile
import os
from pydantic import BaseModel
import pdfplumber

DEPT_NAME_TO_CODE: dict[str, str] = {
    "Civil Engineering": "CE",
    "Aerospace Engineering": "AE",
    "Chemical Engineering": "CH",
    "Mechanical Engineering": "ME",
    "Electrical Engineering": "EE",
    "Computer Science and Engineering": "CS",
    "Computer Science": "CS",
    "Engineering Design": "ED",
    "Ocean Engineering": "OE",
    "Metallurgical and Materials Engineering": "MM",
    "Engineering Physics": "EP",
    "Applied Mechanics": "AM",
    "Biological Engineering": "BE",
    "Biotechnology": "BT",
    "Naval Architecture and Ocean Engineering": "NA",
    "Physics": "PH",
    "Mathematics": "MA",
    "Humanities and Social Sciences": "HS",
    "Artificial Intelligence": "AIDA",
    "Artificial Intelligence and Data Science": "AIDA",
    "AI and Data Science": "AIDA",
    "AI & Data Science": "AIDA",
}

# Matches a course row in the linear grade card format:
# TermNo  CourseCode  CourseTitle  Credits  Grade  Attendance  Year
# e.g.:  01 CV1030 Building Drawing and Visualization 6 A VG 2024
_COURSE_ROW_RE = re.compile(
    r'^(\d{2})\s+'                           # Term number (01, 02, …)
    r'([A-Z]{2,4}\d{3,6}[A-Z0-9]*\*?)\s+'  # Course code (may end in letter, digit, or *)
    r'(.+?)\s+'                              # Course title (non-greedy)
    r'(\d+)\s+'                              # Credits
    r'([A-Z]{1,2})\s+'                      # Grade (A, B, S, P, W …)
    r'[A-Z]+\s+'                            # Attendance category (VG, G, M — skipped)
    r'\d{4}$',                              # Year of passing
    re.MULTILINE,
)


class CourseRecord(BaseModel):
    course_no: str
    title: str
    credits: int
    grade: str


class StudentProfile(BaseModel):
    roll_no: str
    name: str
    dept_code: str
    department_full: str
    batch: int          # entry year e.g. 2024
    program: str        # "BTech" or "DD"
    cgpa: float
    current_semester: int
    next_semester: int
    courses_taken: list[CourseRecord]
    completed_course_nos: list[str]   # serializable set (frontend echoes this back)


def get_semester_from_batch(batch_year: int) -> tuple[int, int]:
    """
    Return (current_semester, next_semester) from batch year + today's date.

    IITM calendar:
      Odd semesters  (1, 3, 5 …) start in July   of batch_year + k
      Even semesters (2, 4, 6 …) start in January of batch_year + k

    'current' = the highest semester that has already started.
    'next'    = current + 1  (the one the student is planning for).

    This is intentionally independent of the grade card term count so that
    summer / extra-term courses don't shift the planning semester.
    """
    now = datetime.datetime.now()
    diff = now.year - batch_year

    # Last odd semester to have started (starts July)
    odd = (2 * diff + 1) if now.month >= 7 else (2 * (diff - 1) + 1)

    # Last even semester to have started (starts January)
    even = 2 * diff

    current = max(odd, even, 1)
    return current, current + 1


def parse_grade_card(file_bytes: bytes) -> StudentProfile:
    """
    Parse an IITM linear grade card PDF and return a structured StudentProfile.

    The linear grade card format looks like:
        Roll No: CE24B102 Name: RISHAV KUMAR
        Department: Civil Engineering
        B.Tech Civil Engineering
        Term No  Course Title  Credit  Grade  Attendance  Year Of Passing
        01 CV1030 Building Drawing and Visualization 6 A VG 2024
        ...
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        full_text = ""
        with pdfplumber.open(tmp_path) as pdf:
            for page in pdf.pages:
                full_text += (page.extract_text() or "") + "\n"
    finally:
        os.unlink(tmp_path)

    if not full_text.strip():
        raise ValueError(
            "Could not extract text from PDF. "
            "Please ensure it is not a scanned image."
        )

    # ── Roll number ──────────────────────────────────────────────────────────
    roll_m = re.search(r"Roll No[.:\s]+([A-Z0-9]+)", full_text)
    if not roll_m:
        raise ValueError(
            "Could not find Roll No in the PDF. Is this an IITM grade card?"
        )
    roll_no = roll_m.group(1).strip()

    # ── Name — same line as Roll No; stop at first newline ───────────────────
    name_m = re.search(r"Name[.:\s]+([A-Z][^\n]+?)(?=\s*\n|$)", full_text)
    name = name_m.group(1).strip() if name_m else "Unknown"

    # ── Department — stop at end of that line ────────────────────────────────
    dept_m = re.search(r"Department[.:\s]+([^\n]+)", full_text)
    dept_full = dept_m.group(1).strip() if dept_m else ""

    # ── Dept code: try name map, fall back to roll number prefix ─────────────
    dept_code = _resolve_dept_code(roll_no, dept_full)

    # ── CGPA ─────────────────────────────────────────────────────────────────
    cgpa_m = re.search(r"average secured.*?is\s*([\d.]+)", full_text, re.IGNORECASE | re.DOTALL)
    cgpa = float(cgpa_m.group(1)) if cgpa_m else 0.0

    # ── Batch + program from roll number: CE24B102 → batch=2024, program=BTech ─
    rn_m = re.match(r'^([A-Z]{2,4})(\d{2})([BD])', roll_no)
    if rn_m:
        batch = 2000 + int(rn_m.group(2))
        program = "BTech" if rn_m.group(3) == "B" else "DD"
    else:
        batch = datetime.datetime.now().year - 2
        program = "BTech"

    # ── Course rows ───────────────────────────────────────────────────────────
    courses_taken: list[CourseRecord] = []
    completed_nos: list[str] = []

    for m in _COURSE_ROW_RE.finditer(full_text):
        code    = m.group(2).rstrip("*").strip()   # remove trailing * marker
        title   = m.group(3).strip()
        credits = int(m.group(4))
        grade   = m.group(5).strip()

        courses_taken.append(CourseRecord(
            course_no=code,
            title=title,
            credits=credits,
            grade=grade,
        ))
        # W = withdrawn, I = incomplete — anything else counts as completed
        if grade not in ("W", "I", ""):
            completed_nos.append(code)

    # Always derive from roll number batch year + today's date.
    # Never use grade card term count — summer/extra-term courses would
    # inflate it and show the wrong planning semester.
    current_sem, next_sem = get_semester_from_batch(batch)

    return StudentProfile(
        roll_no=roll_no,
        name=name,
        dept_code=dept_code,
        department_full=dept_full or dept_code,
        batch=batch,
        program=program,
        cgpa=cgpa,
        current_semester=current_sem,
        next_semester=next_sem,
        courses_taken=courses_taken,
        completed_course_nos=completed_nos,
    )


def _resolve_dept_code(roll_no: str, dept_full: str) -> str:
    for name, code in DEPT_NAME_TO_CODE.items():
        if dept_full.lower().startswith(name.lower()):
            return code
    m = re.match(r'^([A-Z]{2,4})\d{2}', roll_no)
    return m.group(1) if m else "XX"


def generate_suggested_questions(profile: StudentProfile) -> list[str]:
    suggestions = ["Suggest some 9-credit electives for my free slots"]
    hs_count = sum(1 for c in profile.courses_taken if c.course_no.startswith("HS"))
    if hs_count >= 2:
        suggestions.append("Show me more humanities electives")
    else:
        suggestions.append("Which humanities elective suits me?")
    suggestions.append("Find management courses")
    if profile.cgpa >= 8.0:
        suggestions.append("Suggest advanced or research-level electives")
    else:
        suggestions.append("Show me courses with lighter workload")
    return suggestions
