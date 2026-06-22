import json
import json_repair
import logging

logger = logging.getLogger(__name__)


def safe_parse_json(raw: str) -> dict | None:
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        raw = "\n".join(lines)

    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
            return parsed[0]
    except json.JSONDecodeError:
        pass

    try:
        repaired = json_repair.repair_json(raw, return_objects=True)
        if isinstance(repaired, dict):
            return repaired
        if isinstance(repaired, list) and repaired and isinstance(repaired[0], dict):
            return repaired[0]
    except Exception:
        pass

    logger.warning("Failed to parse LLM JSON output after repair attempt")
    return None


def validate_resume_json(data: dict) -> tuple[dict, float]:
    confidence = 1.0
    issues = []

    identity = data.get("identity", {})
    if not identity.get("full_name"):
        confidence = 0.0
        issues.append("No name found")

    experience = data.get("experience", [])
    education = data.get("education", [])
    if not experience and not education:
        confidence = max(confidence - 0.3, 0)
        issues.append("No experience or education found")

    skills = data.get("skills", {})
    if not skills.get("original") and not skills.get("normalized"):
        confidence = max(confidence - 0.1, 0)

    total_exp = data.get("total_experience_months", 0)
    if total_exp and total_exp > 600:
        confidence = max(confidence - 0.2, 0)
        issues.append("Implausible experience duration")

    if not identity.get("headline") and not identity.get("location"):
        confidence = max(confidence - 0.1, 0)

    if issues:
        logger.info(f"Resume validation issues: {issues}")

    return data, round(confidence, 2)


def validate_jd_json(data: dict) -> dict:
    result = {
        "role": data.get("role"),
        "required_skills": data.get("required_skills", []),
        "preferred_skills": data.get("preferred_skills", []),
        "experience": data.get("experience", {"min_years": None, "max_years": None}),
        "location": data.get("location"),
        "industry": data.get("industry"),
    }
    if isinstance(result["required_skills"], str):
        result["required_skills"] = [s.strip() for s in result["required_skills"].split(",")]
    if isinstance(result["preferred_skills"], str):
        result["preferred_skills"] = [s.strip() for s in result["preferred_skills"].split(",")]
    return result
