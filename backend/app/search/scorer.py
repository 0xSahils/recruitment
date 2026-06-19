from thefuzz import fuzz
import logging

logger = logging.getLogger(__name__)

WEIGHTS = {
    "semantic": 0.50,
    "skill": 0.25,
    "role": 0.15,
    "experience": 0.10,
}


def compute_skill_score(
    candidate_skills: list[str],
    required_skills: list[str],
    preferred_skills: list[str],
) -> float:
    if not required_skills and not preferred_skills:
        return 50.0

    candidate_lower = {s.lower() for s in candidate_skills}
    total_weight = 0
    matched_weight = 0

    for skill in required_skills:
        total_weight += 2
        if skill.lower() in candidate_lower:
            matched_weight += 2
        else:
            for cs in candidate_lower:
                if fuzz.ratio(skill.lower(), cs) >= 80:
                    matched_weight += 1.5
                    break

    for skill in preferred_skills:
        total_weight += 1
        if skill.lower() in candidate_lower:
            matched_weight += 1
        else:
            for cs in candidate_lower:
                if fuzz.ratio(skill.lower(), cs) >= 80:
                    matched_weight += 0.7
                    break

    if total_weight == 0:
        return 50.0
    return min((matched_weight / total_weight) * 100, 100)


def compute_role_score(candidate_role: str, candidate_headline: str, jd_role: str | None) -> float:
    if not jd_role:
        return 50.0
    candidate_text = f"{candidate_role} {candidate_headline}".lower()
    jd_lower = jd_role.lower()
    score = fuzz.partial_ratio(jd_lower, candidate_text)
    return min(score, 100)


def compute_experience_score(
    candidate_months: int,
    min_years: int | None,
    max_years: int | None,
) -> float:
    if min_years is None and max_years is None:
        return 50.0

    candidate_years = candidate_months / 12

    if min_years and max_years:
        if min_years <= candidate_years <= max_years:
            return 100.0
        elif candidate_years < min_years:
            diff = min_years - candidate_years
            return max(100 - diff * 20, 0)
        else:
            diff = candidate_years - max_years
            return max(100 - diff * 10, 30)
    elif min_years:
        if candidate_years >= min_years:
            return 100.0
        diff = min_years - candidate_years
        return max(100 - diff * 20, 0)
    elif max_years:
        if candidate_years <= max_years:
            return 100.0
        diff = candidate_years - max_years
        return max(100 - diff * 10, 30)

    return 50.0


def score_candidate(
    candidate: dict,
    parsed_jd: dict,
) -> dict:
    payload = candidate.get("payload", {})

    reranker_score = candidate.get("reranker_score") or 0
    semantic_raw = _normalize_reranker_score(float(reranker_score))

    candidate_skills = payload.get("normalized_skills", [])
    skill_raw = compute_skill_score(
        candidate_skills,
        parsed_jd.get("required_skills", []),
        parsed_jd.get("preferred_skills", []),
    )

    role_raw = compute_role_score(
        payload.get("current_role", ""),
        payload.get("headline", ""),
        parsed_jd.get("role"),
    )

    exp = parsed_jd.get("experience", {})
    exp_raw = compute_experience_score(
        payload.get("total_experience_months", 0),
        exp.get("min_years"),
        exp.get("max_years"),
    )

    semantic_weighted = semantic_raw * WEIGHTS["semantic"]
    skill_weighted = skill_raw * WEIGHTS["skill"]
    role_weighted = role_raw * WEIGHTS["role"]
    exp_weighted = exp_raw * WEIGHTS["experience"]

    total = semantic_weighted + skill_weighted + role_weighted + exp_weighted

    candidate["match_score"] = round(total, 1)
    candidate["score_breakdown"] = {
        "semantic": round(semantic_weighted, 1),
        "skill": round(skill_weighted, 1),
        "role": round(role_weighted, 1),
        "experience": round(exp_weighted, 1),
    }

    return candidate


def _normalize_reranker_score(score: float) -> float:
    import math
    normalized = 1 / (1 + math.exp(-score))
    return normalized * 100


def score_all_candidates(candidates: list[dict], parsed_jd: dict) -> list[dict]:
    scored = [score_candidate(c, parsed_jd) for c in candidates]
    scored.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    return scored
