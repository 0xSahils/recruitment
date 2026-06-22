from datetime import date, datetime
import re
import logging

logger = logging.getLogger(__name__)

MONTH_MAP = {
    "jan": 1, "january": 1, "feb": 2, "february": 2,
    "mar": 3, "march": 3, "apr": 4, "april": 4,
    "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def parse_date(date_str: str | None) -> date | None:
    if not date_str:
        return None
    date_str = date_str.strip()
    if date_str.lower() in ("present", "current", "now", "ongoing", "till now", "till date"):
        return None

    for fmt in (
        "%Y-%m", "%Y-%m-%d", "%Y",
        "%b %Y", "%B %Y",
        "%d %b %Y", "%d %B %Y",
        "%d/%m/%Y", "%m/%Y",
        "%d-%m-%Y", "%m-%Y",
        "%d %b, %Y", "%d %B, %Y",
        "%b %d, %Y", "%B %d, %Y",
    ):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.date()
        except ValueError:
            continue

    month_year = re.match(r"(\w+)\s+(\d{4})", date_str, re.IGNORECASE)
    if month_year:
        m = MONTH_MAP.get(month_year.group(1).lower())
        if m:
            return date(int(month_year.group(2)), m, 1)

    year_match = re.search(r"(\d{4})", date_str)
    if year_match:
        return date(int(year_match.group(1)), 1, 1)
    return None


def compute_experience_months(experiences: list[dict]) -> int:
    total = 0
    for exp in experiences:
        start = parse_date(exp.get("start_date"))
        end = parse_date(exp.get("end_date"))
        if start:
            if not end:
                end = date.today()
            months = (end.year - start.year) * 12 + (end.month - start.month)
            total += max(months, 0)
    return total


def sanitize_parsed_data(data: dict) -> dict:
    identity = data.get("identity", {})
    if isinstance(identity, str):
        identity = {"full_name": identity}
        data["identity"] = identity
    if not isinstance(identity, dict):
        identity = {}
        data["identity"] = identity

    if not identity.get("full_name"):
        identity["full_name"] = "Unknown"

    for field in ("headline", "location", "email", "phone", "linkedin_url"):
        val = identity.get(field)
        if isinstance(val, list):
            identity[field] = val[0] if val else None
        elif val and str(val).lower() in ("null", "none", "n/a", "na", ""):
            identity[field] = None

    if not isinstance(data.get("experience", []), list):
        data["experience"] = []
    if not isinstance(data.get("education", []), list):
        data["education"] = []

    for exp in data["experience"]:
        if not isinstance(exp, dict):
            continue
        for f in ("start_date", "end_date"):
            val = exp.get(f)
            if isinstance(val, str) and val.lower() in ("present", "current", "now", "ongoing", "null", "none"):
                exp[f] = None

    skills = data.get("skills", {})
    if isinstance(skills, list):
        data["skills"] = {"original": skills, "normalized": skills}
    elif not isinstance(skills, dict):
        data["skills"] = {"original": [], "normalized": []}

    if "other_sections" not in data:
        data["other_sections"] = {
            "certifications": [], "projects": [], "publications": [],
            "languages": [], "awards": []
        }

    computed_months = compute_experience_months(data.get("experience", []))
    if computed_months > 0:
        data["total_experience_months"] = computed_months
    elif not data.get("total_experience_months"):
        data["total_experience_months"] = 0

    llm_months = data.get("total_experience_months", 0)
    if isinstance(llm_months, str):
        try:
            data["total_experience_months"] = int(llm_months)
        except ValueError:
            data["total_experience_months"] = computed_months

    return data
