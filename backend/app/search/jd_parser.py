from app.llm.client import generate
from app.llm.prompts import JD_PARSE_SYSTEM, JD_PARSE_PROMPT
from app.llm.parsers import safe_parse_json, validate_jd_json
import logging

logger = logging.getLogger(__name__)


async def parse_jd(query_text: str) -> dict:
    prompt = JD_PARSE_PROMPT.format(query_text=query_text)
    try:
        raw = await generate(prompt, system=JD_PARSE_SYSTEM)
        parsed = safe_parse_json(raw)
        if parsed is None:
            logger.warning("JD parse returned invalid JSON, using fallback")
            return _fallback_parse(query_text)
        return validate_jd_json(parsed)
    except Exception as e:
        logger.error(f"JD parsing failed: {e}")
        return _fallback_parse(query_text)


def _fallback_parse(query_text: str) -> dict:
    return {
        "role": None,
        "required_skills": [],
        "preferred_skills": [],
        "experience": {"min_years": None, "max_years": None},
        "location": None,
        "industry": None,
    }
