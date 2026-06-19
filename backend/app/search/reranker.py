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
        doc = payload.get("profile_text", "")
        if not doc:
            doc = f"{payload.get('full_name', '')} {payload.get('headline', '')} {payload.get('current_role', '')} {' '.join(payload.get('normalized_skills', []))}"
        documents.append(doc)

    ranked = rerank(query_text, documents, top_n=top_n)

    reranked = []
    for idx, score in ranked:
        candidate = candidates[idx].copy()
        candidate["reranker_score"] = score
        reranked.append(candidate)

    return reranked
