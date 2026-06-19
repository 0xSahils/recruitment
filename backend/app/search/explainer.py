from thefuzz import fuzz
import logging

logger = logging.getLogger(__name__)


def generate_explanation(candidate: dict, parsed_jd: dict) -> list[str]:
    payload = candidate.get("payload", {})
    explanations = []

    candidate_skills = set(s.lower() for s in payload.get("normalized_skills", []))
    required = parsed_jd.get("required_skills", [])
    preferred = parsed_jd.get("preferred_skills", [])

    matched_required = [s for s in required if s.lower() in candidate_skills or
                        any(fuzz.ratio(s.lower(), cs) >= 80 for cs in candidate_skills)]
    matched_preferred = [s for s in preferred if s.lower() in candidate_skills or
                         any(fuzz.ratio(s.lower(), cs) >= 80 for cs in candidate_skills)]

    if matched_required:
        explanations.append(f"Has required skills: {', '.join(matched_required)}")
    if matched_preferred:
        explanations.append(f"Has preferred skills: {', '.join(matched_preferred)}")

    exp_months = payload.get("total_experience_months", 0)
    exp_years = round(exp_months / 12, 1)
    current_role = payload.get("current_role", "")
    current_company = payload.get("current_company", "")
    jd_exp = parsed_jd.get("experience", {})
    min_years = jd_exp.get("min_years")

    if current_role and current_company:
        explanations.append(f"Currently {current_role} at {current_company}")

    if min_years:
        if exp_years >= min_years:
            explanations.append(f"{exp_years} years experience meets {min_years}+ year requirement")
        else:
            explanations.append(f"{exp_years} years experience ({min_years}+ preferred)")

    jd_location = parsed_jd.get("location")
    candidate_location = payload.get("location", "")
    if jd_location and candidate_location:
        if fuzz.partial_ratio(jd_location.lower(), candidate_location.lower()) >= 70:
            explanations.append(f"Location match: {candidate_location}")

    jd_role = parsed_jd.get("role")
    if jd_role and current_role:
        if fuzz.partial_ratio(jd_role.lower(), current_role.lower()) >= 60:
            explanations.append(f"Role aligns with {jd_role}")

    if not explanations:
        score = candidate.get("match_score", 0)
        explanations.append(f"Semantic similarity score: {score}")

    return explanations[:4]


def add_explanations(candidates: list[dict], parsed_jd: dict) -> list[dict]:
    for c in candidates:
        c["match_explanation"] = generate_explanation(c, parsed_jd)
    return candidates
