import pandas as pd
import re
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# Normalize inconsistent dept codes across files
DEPT_CODE_NORM = {
    "AI&DS": "AIDA", "AI&DA": "AIDA", "AIDA": "AIDA",
    "AE": "AE", "BE": "BE", "CH": "CH", "CE": "CE",
    "CS": "CS", "EE": "EE", "ME": "ME", "MM": "MM",
    "EP": "EP", "AM": "AM", "NA": "NA", "PH": "PH",
    "BS": "BS", "ED": "ED", "OE": "OE", "MA": "MA",
}

# Category codes used in credit_requirement.csv
CREDIT_CAT_COLS = {
    "E":  "Engineering (E)",
    "C":  "Computing (C)",
    "PC": "Professional (P) Core",
    "PE": "Professional (P) Elective",
    "H":  "Humanities (H)",
    "SC": "Sciences (S) Core",
    "SE": "Sciences (S) Elective",
    "G":  "General (G)",
    "M":  "Management (M)",
}

# Maps course category codes (in sem_wise/master catalog) to credit-req columns
CAT_CODE_TO_CREDIT_KEY = {
    "E": "E", "C": "C",
    "P": "PC",   # Professional core
    "PE": "PE",  # Professional elective
    "H": "H",
    "S": "SC",   # Sciences core
    "SE": "SE",
    "G": "G",
    "M": "M",
    "FRE": "PE", # Free elective → counts as professional elective credit-wise
    "MNS": "PE",
}


class CourseDB:
    def __init__(self):
        self.catalog_df: pd.DataFrame = pd.DataFrame()
        self.sem_wise_df: pd.DataFrame = pd.DataFrame()
        self.slotwise_df: pd.DataFrame = pd.DataFrame()
        self.credit_req_df: pd.DataFrame = pd.DataFrame()
        self.minor_map: dict[str, list[str]] = {}
        self.course_type_map: dict[str, str] = {}

    def load_all_data(self):
        self.catalog_df = self._load_catalog()
        self.sem_wise_df = self._load_sem_wise()
        self.slotwise_df = self._load_slotwise()
        self.credit_req_df = self._load_credit_req()
        self.minor_map = self._parse_minor_txt()
        self.course_type_map = self._load_course_type()
        print(f"CourseDB loaded: {len(self.catalog_df)} catalog, "
              f"{len(self.sem_wise_df)} sem_wise, {len(self.slotwise_df)} slotwise rows")

    # ── Loaders ────────────────────────────────────────────────────────────

    def _load_catalog(self) -> pd.DataFrame:
        df = pd.read_csv(os.path.join(DATA_DIR, "master_course_catalog_final.csv"))
        df["Slot"] = df["Slot"].fillna("").astype(str).str.strip()
        df["Department"] = df["Department"].str.strip().map(
            lambda d: DEPT_CODE_NORM.get(d, d))
        df["Description"] = df["Description"].fillna("")
        return df

    def _load_sem_wise(self) -> pd.DataFrame:
        df = pd.read_csv(os.path.join(DATA_DIR, "sem_wise_details.csv"))
        # Normalize column name
        df.rename(columns={"Course Number": "CourseNo"}, inplace=True)
        df["CourseNo"] = df["CourseNo"].astype(str).str.strip()
        df["Department"] = df["Department"].str.strip().map(
            lambda d: DEPT_CODE_NORM.get(d, d))
        return df

    def _load_slotwise(self) -> pd.DataFrame:
        df = pd.read_csv(os.path.join(DATA_DIR, "slotwise_details_cleaned.csv"))
        df["Slot"] = df["Slot"].fillna("").astype(str).str.strip()
        df["BaseCourseNo"] = df["BaseCourseNo"].astype(str).str.strip()
        df["Prerequisite"] = df["Prerequisite"].fillna("Nil").astype(str)
        df["OfferedforBTechDD"] = df["OfferedforBTechDD"].fillna("No").astype(str).str.strip()
        df["NewCredit"] = pd.to_numeric(df["NewCredit"], errors="coerce").fillna(0).astype(int)
        return df

    def _load_credit_req(self) -> pd.DataFrame:
        df = pd.read_csv(os.path.join(DATA_DIR, "credit_requirement.csv"))
        df["Dept"] = df["Dept"].str.strip().map(lambda d: DEPT_CODE_NORM.get(d, d))
        return df

    def _parse_minor_txt(self) -> dict[str, list[str]]:
        path = os.path.join(DATA_DIR, "minor.txt")
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()

        minor_map: dict[str, list[str]] = {}
        # Collect stream names from the numbered list at the top
        stream_names = re.findall(r'^\d+\.\s+(.+)$', text, re.MULTILINE)
        course_code_re = re.compile(r'^([A-Z]{2,4}\d{4,})', re.MULTILINE)

        # Split text into blocks by stream name
        for name in stream_names:
            escaped = re.escape(name)
            pattern = re.compile(rf'^{escaped}\s*$', re.MULTILINE)
            m = pattern.search(text)
            if not m:
                continue
            start = m.end()
            # Find the next stream heading or end of file
            next_headings = [re.escape(n) for n in stream_names if n != name]
            if next_headings:
                boundary = re.search(
                    r'^(' + '|'.join(next_headings) + r')\s*$',
                    text[start:], re.MULTILINE)
                block = text[start: start + boundary.start()] if boundary else text[start:]
            else:
                block = text[start:]
            codes = course_code_re.findall(block)
            if codes:
                minor_map[name] = codes
        return minor_map

    def _load_course_type(self) -> dict[str, str]:
        df = pd.read_csv(os.path.join(DATA_DIR, "course_type.csv"))
        return dict(zip(df["Code"].astype(str).str.strip(),
                        df["Course Category"].astype(str).str.strip()))

    # ── Query helpers ───────────────────────────────────────────────────────

    def get_mandatory_courses(self, dept: str, batch: int, semester: int) -> list[dict]:
        """Return mandatory courses for a dept/batch/semester with slot info from catalog."""
        dept = DEPT_CODE_NORM.get(dept, dept)
        rows = self.sem_wise_df[
            (self.sem_wise_df["Department"] == dept) &
            (self.sem_wise_df["Batch"] == batch) &
            (self.sem_wise_df["Semester"] == semester)
        ]
        results = []
        for _, row in rows.iterrows():
            code = str(row["CourseNo"]).strip()
            # Look up slot from master catalog
            cat_row = self.catalog_df[self.catalog_df["CourseNo"] == code]
            slot = cat_row["Slot"].iloc[0].strip() if not cat_row.empty else ""
            results.append({
                "course_no": code,
                "course_name": str(row.get("Course Name", "")).strip(),
                "credits": int(row.get("Credits", 0)),
                "category": str(row.get("Category", "")).strip(),
                "slot": slot,
            })
        return results

    def get_occupied_slots(self, dept: str, batch: int, semester: int) -> set[str]:
        courses = self.get_mandatory_courses(dept, batch, semester)
        return {c["slot"] for c in courses if c["slot"]}

    def get_available_electives(self, occupied_slots: set[str], program: str = "BTech") -> pd.DataFrame:
        df = self.slotwise_df.copy()
        if program == "BTech":
            df = df[df["OfferedforBTechDD"] == "Yes"]
        # Remove courses in occupied slots
        df = df[~df["Slot"].isin(occupied_slots)]
        # Drop rows with no slot assigned
        df = df[df["Slot"] != ""]
        return df.reset_index(drop=True)

    def get_credits_earned(self, courses_taken: list[dict], dept: str, batch: int) -> dict:
        """
        Compare earned credits per category against requirement.
        Returns {cat_key: {earned, required, remaining, label}}.
        """
        dept = DEPT_CODE_NORM.get(dept, dept)
        req_row = self.credit_req_df[
            (self.credit_req_df["Dept"] == dept) &
            (self.credit_req_df["Year"] == batch)
        ]

        earned: dict[str, int] = {k: 0 for k in CREDIT_CAT_COLS}

        for course in courses_taken:
            code = str(course.get("course_no", "")).strip()
            credits = int(course.get("credits", 0))
            # Look up category from catalog
            cat_row = self.catalog_df[self.catalog_df["CourseNo"] == code]
            if cat_row.empty:
                continue
            cat = str(cat_row["Category"].iloc[0]).strip()
            key = CAT_CODE_TO_CREDIT_KEY.get(cat)
            if key:
                earned[key] = earned.get(key, 0) + credits

        result = {}
        for key, col in CREDIT_CAT_COLS.items():
            req = 0
            if not req_row.empty and col in req_row.columns:
                req = int(req_row[col].iloc[0])
            e = earned.get(key, 0)
            result[key] = {
                "label": col,
                "earned": e,
                "required": req,
                "remaining": max(0, req - e),
            }
        return result

    def get_minor_courses(self, minor_name: str) -> list[str]:
        return self.minor_map.get(minor_name, [])

    def list_minors(self) -> list[str]:
        return sorted(self.minor_map.keys())

    def get_course_description(self, course_no: str) -> str:
        row = self.catalog_df[self.catalog_df["CourseNo"] == course_no]
        if row.empty:
            return ""
        return str(row["Description"].iloc[0])


# Singleton instance — imported by main.py and recommender.py
db = CourseDB()
