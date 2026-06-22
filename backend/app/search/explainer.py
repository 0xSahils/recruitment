from thefuzz import fuzz
from app.search.scorer import _skill_match, _canonicalize
import logging

logger = logging.getLogger(__name__)


def generate_explanation(candidate: dict, parsed_jd: dict) -> list[str]:
    payload = candidate.get("payload", {})
    explanations = []
    score_breakdown = candidate.get("score_breakdown", {})

    # --- Skill matches ---
    candidate_skills = {s.lower().strip() for s in payload.get("normalized_skills", []) if s}
    required = parsed_jd.get("required_skills", [])
    preferred = parsed_jd.get("preferred_skills", [])

    matched_req = [s for s in required if _skill_match(s, candidate_skills) > 0]
    missing_req = [s for s in required if _skill_match(s, candidate_skills) == 0]
    matched_pref = [s for s in preferred if _skill_match(s, candidate_skills) > 0]

    if matched_req:
        explanations.append(f"Matches required skills: {', '.join(matched_req)}")
    if missing_req:
        explanations.append(f"Missing: {', '.join(missing_req)}")
    if matched_pref:
        explanations.append(f"Also has: {', '.join(matched_pref)}")

    # --- Role match ---
    current_role = payload.get("current_role", "")
    current_company = payload.get("current_company", "")
    jd_role = parsed_jd.get("role", "")

    if current_role and current_company:
        role_str = f"Currently {current_role} at {current_company}"
        if jd_role and fuzz.partial_ratio(jd_role.lower(), current_role.lower()) >= 70:
            role_str += f" (matches \"{jd_role}\")"
        explanations.append(role_str)
    elif current_role:
        explanations.append(f"Current role: {current_role}")

    # --- Experience ---
    exp_months = payload.get("total_experience_months", 0)
    exp_years = round(exp_months / 12, 1)
    jd_exp = parsed_jd.get("experience", {})
    min_years = jd_exp.get("min_years")
    max_years = jd_exp.get("max_years")

    if min_years and max_years:
        if min_years <= exp_years <= max_years:
            explanations.append(f"{exp_years}yr experience fits {min_years}-{max_years}yr range")
        else:
            explanations.append(f"{exp_years}yr experience ({min_years}-{max_years}yr wanted)")
    elif min_years:
        if exp_years >= min_years:
            explanations.append(f"{exp_years}yr experience meets {min_years}+ requirement")
        else:
            explanations.append(f"{exp_years}yr experience ({min_years}+ wanted)")

    # --- Location ---
    jd_location = parsed_jd.get("location")
    candidate_location = payload.get("location", "")
    if jd_location and candidate_location:
        if fuzz.partial_ratio(jd_location.lower(), candidate_location.lower()) >= 70:
            explanations.append(f"Location: {candidate_location}")

    # --- Fallback ---
    if not explanations:
        match_score = candidate.get("match_score", 0)
        if match_score >= 60:
            explanations.append("Strong semantic match based on profile content")
        elif match_score >= 40:
            explanations.append("Moderate profile relevance")
        else:
            explanations.append("Weak match")

    return explanations[:5]


def add_explanations(candidates: list[dict], parsed_jd: dict) -> list[dict]:
    for c in candidates:
        c["match_explanation"] = generate_explanation(c, parsed_jd)
    return candidates
