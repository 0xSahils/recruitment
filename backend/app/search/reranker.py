from app.embeddings.generator import rerank
from app.config import settings
import logging

logger = logging.getLogger(__name__)


def rerank_candidates(
    query_text: str,
    candidates: list[dict],
    top_n: int | None = None,
) -> list[dict]:
    if not candidates:
        return []

    top_n = top_n or settings.RERANK_TOP_N

    documents = []
    for c in candidates:
        payload = c.get("payload", {})
        # Build a rich document for the reranker — include all searchable fields
        parts = []
        if payload.get("full_name"):
            parts.append(payload["full_name"])
        if payload.get("headline"):
            parts.append(payload["headline"])
        if payload.get("current_role"):
            parts.append(f"Role: {payload['current_role']}")
        if payload.get("current_company"):
            parts.append(f"Company: {payload['current_company']}")
        skills = payload.get("normalized_skills", [])
        if skills:
            parts.append(f"Skills: {', '.join(skills)}")
        profile = payload.get("profile_text", "")
        if profile:
            parts.append(profile[:500])
        documents.append(" | ".join(parts) if parts else "")

    try:
        ranked = rerank(query_text, documents, top_n=top_n)
    except Exception as e:
        logger.error(f"Reranking failed: {e}, returning original order")
        for c in candidates:
            c["reranker_score"] = c.get("vector_score", 0)
        return candidates[:top_n]

    reranked = []
    for idx, score in ranked:
        candidate = candidates[idx].copy()
        candidate["reranker_score"] = score
        reranked.append(candidate)

    return reranked
