from thefuzz import fuzz
import math
import logging

logger = logging.getLogger(__name__)

# Skill aliases: maps variant names to canonical form for matching
SKILL_ALIASES = {
    "react": ["reactjs", "react.js", "react js"],
    "node": ["nodejs", "node.js", "node js"],
    "vue": ["vuejs", "vue.js", "vue js"],
    "next.js": ["nextjs", "next js"],
    "nest.js": ["nestjs", "nest js"],
    "angular": ["angularjs", "angular.js"],
    "typescript": ["ts"],
    "javascript": ["js"],
    "python": ["py"],
    "golang": ["go"],
    "kubernetes": ["k8s"],
    "postgresql": ["postgres"],
    "mongodb": ["mongo"],
    "machine learning": ["ml"],
    "artificial intelligence": ["ai"],
    "natural language processing": ["nlp"],
    "deep learning": ["dl"],
    "ci/cd": ["cicd", "ci cd"],
    "c++": ["cpp"],
    "c#": ["csharp", "c sharp"],
    ".net": ["dotnet", "dot net"],
    "elasticsearch": ["elastic search", "elastic"],
    "docker": ["containerization"],
    "aws": ["amazon web services"],
    "azure": ["microsoft azure"],
    "gcp": ["google cloud", "google cloud platform"],
    "devops": ["dev ops"],
    "power bi": ["powerbi"],
    "ui/ux": ["uiux", "ui ux"],
    "mba": ["m.b.a", "master of business administration"],
    "btech": ["b.tech", "b tech", "bachelor of technology"],
    "mtech": ["m.tech", "m tech", "master of technology"],
    "phd": ["ph.d", "doctorate"],
    "mca": ["m.c.a", "master of computer applications"],
    "bca": ["b.c.a", "bachelor of computer applications"],
}

# Build reverse lookup: variant → canonical
_ALIAS_REVERSE: dict[str, str] = {}
for canonical, variants in SKILL_ALIASES.items():
    _ALIAS_REVERSE[canonical] = canonical
    for v in variants:
        _ALIAS_REVERSE[v] = canonical


def _canonicalize(skill: str) -> str:
    s = skill.lower().strip()
    return _ALIAS_REVERSE.get(s, s)


def _skill_match(query_skill: str, candidate_skills: set[str]) -> float:
    """Returns match quality: 1.0 = exact, 0.8 = alias, 0.6 = fuzzy, 0.4 = substring, 0.0 = none."""
    qs = query_skill.lower().strip()
    qc = _canonicalize(qs)

    # Exact or alias match
    for cs in candidate_skills:
        cc = _canonicalize(cs)
        if qc == cc or qs == cs:
            return 1.0

    # Substring match (e.g., "react" in "react native")
    for cs in candidate_skills:
        if qs in cs or cs in qs:
            return 0.4

    # Fuzzy match
    for cs in candidate_skills:
        if fuzz.ratio(qs, cs) >= 80:
            return 0.6

    return 0.0


def compute_skill_score(
    candidate_skills: list[str],
    required_skills: list[str],
    preferred_skills: list[str],
    profile_text: str = "",
) -> float | None:
    if not required_skills and not preferred_skills:
        return None

    candidate_lower = {s.lower().strip() for s in candidate_skills if s}
    profile_lower = profile_text.lower()

    total_weight = 0.0
    matched_weight = 0.0

    for skill in required_skills:
        total_weight += 2.0
        match = _skill_match(skill, candidate_lower)
        if match > 0:
            matched_weight += 2.0 * match
        else:
            sl = skill.lower()
            canon = _canonicalize(sl)
            variants = [sl, canon] + SKILL_ALIASES.get(canon, [])
            found_in_profile = any(v in profile_lower for v in variants)
            if found_in_profile:
                matched_weight += 2.0 * 0.7

    for skill in preferred_skills:
        total_weight += 1.0
        match = _skill_match(skill, candidate_lower)
        if match > 0:
            matched_weight += 1.0 * match
        else:
            sl = skill.lower()
            canon = _canonicalize(sl)
            variants = [sl, canon] + SKILL_ALIASES.get(canon, [])
            found_in_profile = any(v in profile_lower for v in variants)
            if found_in_profile:
                matched_weight += 1.0 * 0.7

    if total_weight == 0:
        return None
    return min((matched_weight / total_weight) * 100, 100)


def compute_role_score(
    candidate_role: str,
    candidate_headline: str,
    jd_role: str | None,
) -> float | None:
    if not jd_role:
        return None

    jd_lower = jd_role.lower().strip()
    role_lower = (candidate_role or "").lower().strip()
    headline_lower = (candidate_headline or "").lower().strip()
    combined = f"{role_lower} {headline_lower}".strip()

    if not combined:
        return 0.0

    # Direct role title match
    if jd_lower in role_lower or role_lower in jd_lower:
        return 100.0

    # Headline contains the role
    if jd_lower in headline_lower:
        return 95.0

    # Fuzzy match against role
    role_score = fuzz.partial_ratio(jd_lower, role_lower) if role_lower else 0
    headline_score = fuzz.partial_ratio(jd_lower, headline_lower) if headline_lower else 0
    best = max(role_score, headline_score)

    if best >= 90:
        return 95.0
    if best >= 80:
        return best * 0.9
    if best >= 60:
        return best * 0.5
    return best * 0.2


def compute_experience_score(
    candidate_months: int,
    min_years: int | None,
    max_years: int | None,
) -> float | None:
    if min_years is None and max_years is None:
        return None

    candidate_years = candidate_months / 12

    if min_years and max_years:
        if min_years <= candidate_years <= max_years:
            return 100.0
        elif candidate_years < min_years:
            diff = min_years - candidate_years
            return max(100 - diff * 25, 0)
        else:
            diff = candidate_years - max_years
            return max(100 - diff * 10, 30)
    elif min_years:
        if candidate_years >= min_years:
            return 100.0
        diff = min_years - candidate_years
        return max(100 - diff * 25, 0)
    elif max_years:
        if candidate_years <= max_years:
            return 100.0
        diff = candidate_years - max_years
        return max(100 - diff * 10, 30)

    return None


def compute_location_score(
    candidate_location: str,
    jd_location: str | None,
) -> float | None:
    if not jd_location:
        return None

    if not candidate_location:
        return 0.0

    jd_lower = jd_location.lower().strip()
    cand_lower = candidate_location.lower().strip()

    if jd_lower in cand_lower or cand_lower in jd_lower:
        return 100.0

    from app.search.retrieval import LOCATION_ALIASES
    jd_aliases = LOCATION_ALIASES.get(jd_lower, [jd_lower])
    for alias in jd_aliases:
        if alias in cand_lower:
            return 100.0

    ratio = fuzz.partial_ratio(jd_lower, cand_lower)
    if ratio >= 80:
        return 80.0

    return 0.0


def _normalize_reranker_score(score: float) -> float:
    # BGE reranker outputs logits typically in [-12, +12]
    # Spread the signal: score=5 → ~95, score=0 → ~50, score=-5 → ~5
    normalized = 1 / (1 + math.exp(-score * 0.6))
    return normalized * 100


def score_candidate(candidate: dict, parsed_jd: dict) -> dict:
    payload = candidate.get("payload", {})

    reranker_score = candidate.get("reranker_score")
    if reranker_score is not None:
        semantic_raw = _normalize_reranker_score(float(reranker_score))
    else:
        semantic_raw = candidate.get("vector_score", 0) * 100

    candidate_skills = payload.get("normalized_skills", [])
    edu_keywords = payload.get("education_keywords", [])
    candidate_skills = candidate_skills + edu_keywords
    profile_text = payload.get("profile_text", "")

    skill_raw = compute_skill_score(
        candidate_skills,
        parsed_jd.get("required_skills", []),
        parsed_jd.get("preferred_skills", []),
        profile_text,
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

    loc_raw = compute_location_score(
        payload.get("location", ""),
        parsed_jd.get("location"),
    )

    # Dynamic weighting: only weight dimensions that the query specifies
    active = {"semantic": 0.40}
    if skill_raw is not None:
        active["skill"] = 0.25
    if role_raw is not None:
        active["role"] = 0.15
    if exp_raw is not None:
        active["experience"] = 0.10
    if loc_raw is not None:
        active["location"] = 0.10

    # Redistribute unused weight to semantic
    non_semantic = sum(v for k, v in active.items() if k != "semantic")
    active["semantic"] = 1.0 - non_semantic

    scores = {
        "semantic": semantic_raw * active["semantic"],
        "skill": (skill_raw or 0) * active.get("skill", 0),
        "role": (role_raw or 0) * active.get("role", 0),
        "experience": (exp_raw or 0) * active.get("experience", 0),
        "location": (loc_raw or 0) * active.get("location", 0),
    }

    total = sum(scores.values())

    candidate["match_score"] = round(total, 1)
    candidate["score_breakdown"] = {
        "semantic": round(scores["semantic"], 1),
        "skill": round(scores["skill"], 1),
        "role": round(scores["role"], 1),
        "experience": round(scores["experience"], 1),
    }

    return candidate


def score_all_candidates(candidates: list[dict], parsed_jd: dict) -> list[dict]:
    scored = [score_candidate(c, parsed_jd) for c in candidates]
    scored.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    return scored
