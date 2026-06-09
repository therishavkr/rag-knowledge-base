"""
Hybrid recommendation engine — three stages:
  1. Hard constraint filtering (pandas) — slot conflicts, prerequisites, credit cap
  2. Semantic ranking (ChromaDB) — match against student interests
  3. Groq LLaMA 3.3 70B — final ranking with 1-sentence explanations
"""

from __future__ import annotations
import re
import json
import pandas as pd
from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage

from course_db import CourseDB, db
from grade_card_parser import StudentProfile
from vector_store import search_chunks
from groq_service import get_llm

SEMESTER_CREDIT_CAP = 64   # IITM per-semester cap; override via preferences

NIL_RE = re.compile(r'^\s*(nil|none|nan|cot|n\.a\.?|-)\s*$', re.IGNORECASE)
COURSE_CODE_RE = re.compile(r'([A-Z]{2,4})\s*(\d{3,5}[A-Z]?)', re.IGNORECASE)


# ── Pydantic models ─────────────────────────────────────────────────────────

class PreferencesForm(BaseModel):
    interests: str = ""
    workload_preference: str = "medium"   # "light" | "medium" | "heavy"
    minor_target: str | None = None
    credit_budget: int = SEMESTER_CREDIT_CAP
    free_text: str = ""                   # extra notes from chat or form


class CourseRecommendation(BaseModel):
    course_no: str
    course_name: str
    slot: str
    credits: int
    instructor: str
    explanation: str = ""
    minor_aligned: bool = False
    semantic_score: float = 0.0


class RecommendationResult(BaseModel):
    mandatory_courses: list[dict]
    occupied_slots: list[str]
    recommended_electives: list[CourseRecommendation]
    also_consider: list[CourseRecommendation]
    credit_summary: dict
    minor_progress: dict | None = None


# ── Prerequisite helpers ──────────────────────────────────────────────────

def _parse_prerequisites(prereq_str: str) -> tuple[list[str], str]:
    """Return (course_codes, logic) where logic is 'AND' or 'OR'."""
    s = str(prereq_str).strip()
    if NIL_RE.match(s) or not s:
        return [], "AND"
    logic = "OR" if re.search(r'\bor\b', s, re.IGNORECASE) else "AND"
    matches = COURSE_CODE_RE.findall(s)
    codes = [f"{dept.upper()}{num.upper()}" for dept, num in matches]
    return codes, logic


def _prerequisites_met(prereq_str: str, completed: set[str]) -> bool:
    codes, logic = _parse_prerequisites(prereq_str)
    if not codes:
        return True
    if logic == "OR":
        return any(c in completed for c in codes)
    return all(c in completed for c in codes)


# ── Stage 1: Hard constraint filtering ───────────────────────────────────

def _stage1_filter(
    profile: StudentProfile,
    prefs: PreferencesForm,
    course_db: CourseDB,
) -> tuple[pd.DataFrame, list[dict], set[str], int]:
    """
    Returns (filtered_electives_df, mandatory_courses, occupied_slots, mandatory_credits).
    """
    mandatory = course_db.get_mandatory_courses(
        profile.dept_code, profile.batch, profile.next_semester
    )
    occupied_slots = {c["slot"] for c in mandatory if c["slot"]}
    mandatory_credits = sum(c["credits"] for c in mandatory)
    available_budget = prefs.credit_budget - mandatory_credits

    completed_set = set(profile.completed_course_nos)

    # Get slot-conflict-free electives
    candidates = course_db.get_available_electives(occupied_slots, profile.program)

    # Prerequisite check
    mask = candidates["Prerequisite"].apply(
        lambda p: _prerequisites_met(str(p), completed_set)
    )
    candidates = candidates[mask]

    # Credit cap: keep only courses that individually fit in remaining budget
    if available_budget > 0:
        candidates = candidates[candidates["NewCredit"] <= available_budget]

    # Flag minor-aligned courses
    minor_codes: set[str] = set()
    if prefs.minor_target:
        minor_codes = set(course_db.get_minor_courses(prefs.minor_target))
    candidates = candidates.copy()
    candidates["minor_aligned"] = candidates["BaseCourseNo"].isin(minor_codes)

    return candidates, mandatory, occupied_slots, mandatory_credits


# ── Stage 2: Semantic search ──────────────────────────────────────────────

def _stage2_semantic(prefs: PreferencesForm, top_k: int = 30) -> dict[str, float]:
    """
    Returns {course_no: semantic_score} for the top-k semantic hits.
    """
    parts = [prefs.interests, prefs.workload_preference, prefs.free_text]
    query = " ".join(p for p in parts if p).strip() or "interesting elective"

    docs = search_chunks(query, ["courses"], n_results=top_k)
    score_map: dict[str, float] = {}
    for rank, doc in enumerate(docs):
        code = doc.metadata.get("course_no", "")
        if code:
            score_map[code] = float(top_k - rank)
    return score_map


# ── Stage 3: Groq ranking ─────────────────────────────────────────────────

def _stage3_groq_rank(
    candidates: list[dict],
    profile: StudentProfile,
    prefs: PreferencesForm,
) -> list[dict]:
    """
    Send up to 20 candidates to Groq for final ranking + 1-sentence explanations.
    Returns list of {course_no, explanation} in ranked order (top 5).
    Falls back to input order if LLM fails.
    """
    if not candidates:
        return []

    llm = get_llm()

    recent_courses = [c.course_no for c in profile.courses_taken[-8:]]
    course_list_json = json.dumps([
        {
            "course_no": c["course_no"],
            "name": c["course_name"],
            "credits": c["credits"],
            "slot": c["slot"],
            "description": c.get("description", "")[:200],
        }
        for c in candidates[:20]
    ], indent=2)

    system_prompt = (
        "You are an academic advisor for IIT Madras students. "
        "Your job is to rank elective courses for a specific student and give a brief reason for each pick. "
        "Return ONLY a JSON array (no markdown, no extra text) of exactly 5 objects, "
        'each with keys "course_no" (string) and "explanation" (one sentence, max 20 words). '
        "Rank the most suitable course first."
    )
    user_prompt = (
        f"Student profile:\n"
        f"- Department: {profile.dept_code}, Semester {profile.next_semester}, CGPA {profile.cgpa}\n"
        f"- Interests: {prefs.interests or 'not specified'}\n"
        f"- Workload preference: {prefs.workload_preference}\n"
        f"- Minor target: {prefs.minor_target or 'none'}\n"
        f"- Recently completed: {', '.join(recent_courses) or 'none'}\n\n"
        f"Elective candidates:\n{course_list_json}\n\n"
        "Return the top 5 as a JSON array."
    )

    try:
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        raw = response.content.strip()
        # Strip markdown fences if present
        raw = re.sub(r'^```[a-z]*\n?', '', raw).rstrip('` \n')
        ranked = json.loads(raw)
        if isinstance(ranked, list) and ranked:
            return ranked[:5]
    except Exception as e:
        print(f"Groq ranking failed ({e}), falling back to semantic order")

    # Fallback: return first 5 with no explanation
    return [{"course_no": c["course_no"], "explanation": ""} for c in candidates[:5]]


# ── Main entry point ──────────────────────────────────────────────────────

def get_recommendations(
    profile: StudentProfile,
    prefs: PreferencesForm,
    course_db: CourseDB = db,
) -> RecommendationResult:

    # Stage 1
    candidates_df, mandatory, occupied_slots, mandatory_credits = _stage1_filter(
        profile, prefs, course_db
    )

    # Stage 2 — semantic scores
    score_map = _stage2_semantic(prefs)

    # Attach semantic score and enrich with description from catalog
    def _enrich_row(row: pd.Series) -> dict:
        code = row["BaseCourseNo"]
        desc = course_db.get_course_description(code)
        return {
            "course_no": code,
            "course_name": str(row.get("CourseName", "")).strip(),
            "slot": row["Slot"],
            "credits": int(row["NewCredit"]),
            "instructor": str(row.get("InstructorName", "")).strip(),
            "prerequisite": str(row.get("Prerequisite", "")),
            "minor_aligned": bool(row.get("minor_aligned", False)),
            "semantic_score": score_map.get(code, 0.0),
            "description": desc,
        }

    if candidates_df.empty:
        enriched = []
    else:
        enriched = [_enrich_row(row) for _, row in candidates_df.iterrows()]
        # Sort: minor-aligned first, then semantic score descending
        enriched.sort(key=lambda c: (c["minor_aligned"], c["semantic_score"]), reverse=True)

    # Stage 3 — Groq ranks top 20
    top20 = enriched[:20]
    ranked_meta = _stage3_groq_rank(top20, profile, prefs)

    # Build top-5 recommendations (merge Groq ranking with enriched data)
    enriched_map = {c["course_no"]: c for c in top20}
    top5: list[CourseRecommendation] = []
    seen: set[str] = set()
    for item in ranked_meta:
        code = item.get("course_no", "")
        if code in enriched_map and code not in seen:
            c = enriched_map[code]
            top5.append(CourseRecommendation(
                course_no=code,
                course_name=c["course_name"],
                slot=c["slot"],
                credits=c["credits"],
                instructor=c["instructor"],
                explanation=item.get("explanation", ""),
                minor_aligned=c["minor_aligned"],
                semantic_score=c["semantic_score"],
            ))
            seen.add(code)

    # Also-consider: next 5 by semantic score, not already in top5
    also: list[CourseRecommendation] = []
    for c in enriched:
        if c["course_no"] not in seen and len(also) < 5:
            also.append(CourseRecommendation(
                course_no=c["course_no"],
                course_name=c["course_name"],
                slot=c["slot"],
                credits=c["credits"],
                instructor=c["instructor"],
                minor_aligned=c["minor_aligned"],
                semantic_score=c["semantic_score"],
            ))
            seen.add(c["course_no"])

    # Credit summary
    credit_summary = course_db.get_credits_earned(
        [c.model_dump() for c in profile.courses_taken],
        profile.dept_code,
        profile.batch,
    )

    # Minor progress
    minor_progress = None
    if prefs.minor_target:
        minor_courses = course_db.get_minor_courses(prefs.minor_target)
        done = [c for c in minor_courses if c in set(profile.completed_course_nos)]
        minor_progress = {
            "minor_name": prefs.minor_target,
            "total_courses": len(minor_courses),
            "completed": len(done),
            "completed_codes": done,
            "remaining_codes": [c for c in minor_courses if c not in done],
        }

    return RecommendationResult(
        mandatory_courses=mandatory,
        occupied_slots=sorted(occupied_slots),
        recommended_electives=top5,
        also_consider=also,
        credit_summary=credit_summary,
        minor_progress=minor_progress,
    )
