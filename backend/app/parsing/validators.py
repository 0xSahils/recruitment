from datetime import date, datetime
import logging

logger = logging.getLogger(__name__)


def parse_date(date_str: str | None) -> date | None:
    if not date_str:
        return None
    date_str = date_str.strip()
    for fmt in ("%Y-%m", "%Y-%m-%d", "%Y"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.date()
        except ValueError:
            continue
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

    if not identity.get("full_name"):
        identity["full_name"] = "Unknown"

    if not isinstance(data.get("experience", []), list):
        data["experience"] = []
    if not isinstance(data.get("education", []), list):
        data["education"] = []

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

    if not data.get("total_experience_months"):
        data["total_experience_months"] = compute_experience_months(data.get("experience", []))

    return data
