import re
from app.llm.client import generate
from app.llm.prompts import JD_PARSE_SYSTEM, JD_PARSE_PROMPT
from app.llm.parsers import safe_parse_json, validate_jd_json
import logging

logger = logging.getLogger(__name__)

EXP_RE = re.compile(r"(\d+)\+?\s*(?:years?|yrs?)", re.IGNORECASE)
EXP_RANGE_RE = re.compile(r"(\d+)\s*[-–]\s*(\d+)\s*(?:years?|yrs?)", re.IGNORECASE)

# Multi-word skills MUST come before single-word ones so regex matches longest first
COMMON_SKILLS = [
    # Multi-word (order matters — longest first)
    "machine learning", "deep learning", "data science", "power bi",
    "natural language processing", "computer vision", "ci/cd", "ui/ux",
    "node.js", "react native", "vue.js", "next.js", "nest.js",
    "spring boot", "ruby on rails", "scikit-learn",
    "talent intelligence", "market research", "executive search",
    # Single-word
    "python", "java", "javascript", "typescript", "react", "angular", "vue",
    "node", "nodejs", "express", "django", "flask", "fastapi",
    "spring", "docker", "kubernetes", "k8s", "aws", "azure", "gcp",
    "sql", "mysql", "postgres", "postgresql", "mongodb", "redis",
    "git", "linux", "rust", "swift", "kotlin", "flutter", "dart",
    "terraform", "jenkins", "pandas", "numpy", "tensorflow", "pytorch",
    "html", "css", "tailwind", "figma", "devops", "sre",
    "agile", "scrum", "jira", "salesforce", "sap", "tableau",
    "excel", "hadoop", "spark", "kafka", "rabbitmq", "graphql",
    "microservices", "firebase", "supabase", "elasticsearch",
    "altium", "pcb", "circuit", "rf", "antenna", "fiber",
    "recruitment", "talent", "sourcing", "hiring",
    "c++", "c#", ".net", "go", "golang", "php", "perl", "scala",
    "nlp", "ml", "ai", "api", "rest", "grpc",
    "aerospike", "cassandra", "dynamodb", "couchbase",
    "selenium", "cypress", "jest", "pytest", "junit",
    # Education / qualifications (treated as skills for matching)
    "mba", "btech", "b.tech", "mtech", "m.tech", "phd", "mca", "bca",
    "msc", "bsc", "bba", "pgdm",
]

ROLE_PATTERNS = [
    "software engineer", "software developer", "web developer",
    "frontend developer", "backend developer", "full stack developer",
    "fullstack developer", "full-stack developer",
    "data engineer", "data analyst", "data scientist",
    "devops engineer", "sre engineer", "cloud engineer",
    "mobile developer", "ios developer", "android developer",
    "qa engineer", "test engineer", "quality assurance",
    "ml engineer", "machine learning engineer", "ai engineer",
    "technical lead", "tech lead", "engineering manager",
    "product manager", "project manager", "scrum master",
    "solutions architect", "system architect",
    "ui developer", "ux designer", "ui/ux designer",
    "research analyst", "business analyst", "market analyst",
    "talent acquisition", "recruiter", "hr manager",
    "fiber engineer", "hardware engineer", "electrical engineer",
    "mechanical engineer", "civil engineer", "chemical engineer",
    "field engineer", "application engineer", "project engineer",
    "associate", "intern", "trainee", "consultant", "specialist",
    "manager", "director", "lead", "architect", "designer",
    "developer", "engineer", "analyst",
]

LOCATION_KEYWORDS = [
    "new york", "san francisco", "los angeles", "new jersey",
    "uttar pradesh", "tamil nadu", "andhra pradesh", "madhya pradesh",
    "ncr", "bangalore", "bengaluru", "mumbai", "delhi", "noida",
    "gurgaon", "gurugram", "hyderabad", "chennai", "pune", "kolkata",
    "ahmedabad", "jaipur", "lucknow", "chandigarh", "indore",
    "london", "remote", "india", "usa", "us", "uk",
    "karnataka", "maharashtra", "haryana", "rajasthan",
]


INDUSTRY_KEYWORDS = [
    "banking", "finance", "fintech", "insurance", "healthcare", "pharma",
    "telecom", "telecommunications", "ecommerce", "e-commerce", "retail",
    "automotive", "manufacturing", "logistics", "supply chain",
    "education", "edtech", "media", "entertainment", "gaming",
    "real estate", "construction", "energy", "oil and gas",
    "consulting", "legal", "government", "defense", "aerospace",
    "agriculture", "food", "hospitality", "travel", "fmcg",
]


async def parse_jd(query_text: str) -> dict:
    query = query_text.strip()
    words = query.lower().split()

    if len(words) <= 30:
        result = _rule_based_parse(query)
        if result.get("role") or result.get("required_skills"):
            logger.info(f"Rule-based JD parse: {result}")
            return result

    prompt = JD_PARSE_PROMPT.format(query_text=query)
    try:
        raw = await generate(prompt, system=JD_PARSE_SYSTEM)
        parsed = safe_parse_json(raw)
        if not isinstance(parsed, dict):
            logger.warning("JD parse returned invalid JSON, using fallback")
            return _fallback_parse(query)
        return validate_jd_json(parsed)
    except Exception as e:
        logger.error(f"JD parsing failed: {e}")
        return _fallback_parse(query)


def _parse_logical_operators(query: str) -> dict:
    """Parse AND/OR/NOT from query. Returns structured conditions."""
    query_lower = query.lower().strip()

    not_terms = []
    for m in re.finditer(r'\bnot\s+(\w+)', query_lower):
        not_terms.append(m.group(1))
    cleaned = re.sub(r'\bnot\s+\w+', '', query_lower).strip()

    or_groups = []
    if ' or ' in cleaned:
        parts = re.split(r'\s+or\s+', cleaned)
        or_groups = [p.strip() for p in parts if p.strip()]
        cleaned = parts[0]

    cleaned = re.sub(r'\s+and\s+', ' ', cleaned)

    return {
        "cleaned_query": cleaned,
        "not_terms": not_terms,
        "or_groups": or_groups,
    }


def _rule_based_parse(query: str) -> dict:
    logical = _parse_logical_operators(query)
    query_lower = logical["cleaned_query"]

    result = {
        "role": None,
        "required_skills": [],
        "preferred_skills": [],
        "experience": {"min_years": None, "max_years": None},
        "location": None,
        "industry": None,
        "not_terms": logical["not_terms"],
    }

    # Add OR groups as preferred skills (any of them is acceptable)
    for og in logical["or_groups"]:
        og_stripped = og.strip()
        if og_stripped:
            result["preferred_skills"].append(og_stripped)

    # Extract experience
    range_match = EXP_RANGE_RE.search(query_lower)
    if range_match:
        result["experience"]["min_years"] = int(range_match.group(1))
        result["experience"]["max_years"] = int(range_match.group(2))
    else:
        exp_match = EXP_RE.search(query_lower)
        if exp_match:
            result["experience"]["min_years"] = int(exp_match.group(1))

    # Extract location (longest match first)
    for loc in sorted(LOCATION_KEYWORDS, key=len, reverse=True):
        pattern = r"\b" + re.escape(loc) + r"\b"
        if re.search(pattern, query_lower):
            result["location"] = loc.title()
            break

    # Extract industry
    for ind in sorted(INDUSTRY_KEYWORDS, key=len, reverse=True):
        pattern = r"\b" + re.escape(ind) + r"\b"
        if re.search(pattern, query_lower):
            result["industry"] = ind
            result["required_skills"].append(ind)
            break

    # Extract role (longest match first)
    for role in sorted(ROLE_PATTERNS, key=len, reverse=True):
        pattern = r"\b" + re.escape(role) + r"\b"
        if re.search(pattern, query_lower):
            result["role"] = role.title()
            break

    # Extract skills (longest match first, skip if already covered by an alias)
    found_skills = []
    found_canonical = set()
    for skill in COMMON_SKILLS:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, query_lower):
            from app.search.scorer import _canonicalize
            canon = _canonicalize(skill)
            if canon not in found_canonical:
                found_canonical.add(canon)
                found_skills.append(skill)
    result["required_skills"].extend(found_skills)

    # If no explicit role found, build one from the query
    if not result["role"]:
        role_text = query_lower
        role_text = EXP_RANGE_RE.sub("", role_text)
        role_text = EXP_RE.sub("", role_text)
        for loc in LOCATION_KEYWORDS:
            role_text = re.sub(r"\b" + re.escape(loc) + r"\b", "", role_text, flags=re.IGNORECASE)
        for ind in INDUSTRY_KEYWORDS:
            role_text = re.sub(r"\b" + re.escape(ind) + r"\b", "", role_text, flags=re.IGNORECASE)
        for skill in found_skills:
            role_text = re.sub(r"\b" + re.escape(skill) + r"\b", "", role_text, flags=re.IGNORECASE)
        role_text = re.sub(
            r"\b(in|with|at|and|or|not|for|who|has|have|having|need|looking|want|experience|years?|yrs?|of|exp)\b",
            "", role_text, flags=re.IGNORECASE,
        )
        role_text = re.sub(r"[+\-,]", " ", role_text)
        role_text = re.sub(r"\s+", " ", role_text).strip()
        if role_text and len(role_text) > 2:
            result["role"] = role_text

    # If still no role but we have skills, use the primary skill
    if not result["role"] and result["required_skills"]:
        result["role"] = result["required_skills"][0]

    return result


def _fallback_parse(query_text: str) -> dict:
    result = _rule_based_parse(query_text)
    if not result.get("role") and not result.get("required_skills"):
        result["role"] = query_text.strip()
    return result
