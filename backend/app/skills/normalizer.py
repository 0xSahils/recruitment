import yaml
import os
import logging

logger = logging.getLogger(__name__)

_dictionary: dict[str, list[str]] | None = None

DICTIONARY_PATH = os.path.join(os.path.dirname(__file__), "skill_dictionary.yaml")


def _load_dictionary() -> dict[str, list[str]]:
    global _dictionary
    if _dictionary is not None:
        return _dictionary
    try:
        with open(DICTIONARY_PATH, "r") as f:
            _dictionary = yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.warning("Skill dictionary not found, using empty dictionary")
        _dictionary = {}
    return _dictionary


def normalize_skill(skill: str) -> list[str]:
    dictionary = _load_dictionary()
    key = skill.strip().lower()

    for dict_key, expansions in dictionary.items():
        if key == dict_key.lower():
            return expansions

    return [skill.strip()]


def normalize_skills(original_skills: list[str]) -> list[str]:
    all_normalized = []
    seen = set()
    for skill in original_skills:
        for normalized in normalize_skill(skill):
            lower = normalized.lower()
            if lower not in seen:
                seen.add(lower)
                all_normalized.append(normalized)
    return all_normalized


def get_all_normalized_skills(candidate_data: dict) -> list[str]:
    skills_data = candidate_data.get("skills", {})
    original = skills_data.get("original", [])
    already_normalized = skills_data.get("normalized", [])

    from_dictionary = normalize_skills(original)

    all_skills = set()
    for s in from_dictionary:
        all_skills.add(s)
    for s in already_normalized:
        all_skills.add(s)

    return list(all_skills)
