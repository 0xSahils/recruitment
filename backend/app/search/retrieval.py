from qdrant_client import models
from app.vector_db import search_vectors
from app.embeddings.generator import generate_embedding
from app.config import settings
from rank_bm25 import BM25Okapi
import logging

logger = logging.getLogger(__name__)

LOCATION_ALIASES = {
    "bangalore": ["bangalore", "bengaluru", "blr"],
    "bengaluru": ["bangalore", "bengaluru", "blr"],
    "mumbai": ["mumbai", "bombay"],
    "bombay": ["mumbai", "bombay"],
    "delhi": ["delhi", "new delhi", "ncr"],
    "new delhi": ["delhi", "new delhi", "ncr"],
    "ncr": ["delhi", "new delhi", "ncr", "noida", "gurgaon", "gurugram", "faridabad", "greater noida"],
    "gurgaon": ["gurgaon", "gurugram"],
    "gurugram": ["gurgaon", "gurugram"],
    "chennai": ["chennai", "madras"],
    "kolkata": ["kolkata", "calcutta"],
    "hyderabad": ["hyderabad", "hyd"],
    "pune": ["pune"],
    "noida": ["noida", "greater noida"],
}


def build_qdrant_filter(parsed_jd: dict, exclude_rejected: bool = True) -> models.Filter | None:
    conditions = []

    if exclude_rejected:
        conditions.append(
            models.FieldCondition(
                key="candidate_status",
                match=models.MatchExcept(**{"except": ["rejected"]}),
            )
        )

    exp = parsed_jd.get("experience", {})
    min_years = exp.get("min_years")
    if min_years:
        conditions.append(
            models.FieldCondition(
                key="total_experience_months",
                range=models.Range(gte=max(0, (min_years - 1) * 12)),
            )
        )
    max_years = exp.get("max_years")
    if max_years:
        conditions.append(
            models.FieldCondition(
                key="total_experience_months",
                range=models.Range(lte=(max_years + 1) * 12),
            )
        )

    if not conditions:
        return None
    return models.Filter(must=conditions)


def vector_search(query_text: str, parsed_jd: dict, exclude_rejected: bool = True, limit: int = 100) -> list[dict]:
    query_embedding = generate_embedding(query_text)
    qdrant_filter = build_qdrant_filter(parsed_jd, exclude_rejected)
    results = search_vectors(query_embedding, filters=qdrant_filter, limit=limit)

    candidates = []
    for point in results:
        candidates.append({
            "candidate_id": point.payload.get("candidate_id", str(point.id)),
            "vector_score": point.score,
            "payload": point.payload,
        })
    return candidates


def bm25_search(query_text: str, candidate_pool: list[dict], top_n: int = 100) -> list[dict]:
    if not candidate_pool:
        return []

    corpus = []
    for c in candidate_pool:
        payload = c.get("payload", {})
        text = payload.get("profile_text", "")
        skills = " ".join(payload.get("normalized_skills", []))
        role = payload.get("current_role", "")
        headline = payload.get("headline", "")
        corpus.append(f"{text} {skills} {role} {headline}".lower())

    tokenized_corpus = [doc.split() for doc in corpus]
    tokenized_query = query_text.lower().split()

    bm25 = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(tokenized_query)

    for i, c in enumerate(candidate_pool):
        c["bm25_score"] = float(scores[i])

    return candidate_pool


def reciprocal_rank_fusion(
    vector_results: list[dict],
    bm25_results: list[dict],
    k: int = 60,
) -> list[dict]:
    rrf_scores: dict[str, float] = {}
    all_candidates: dict[str, dict] = {}

    vector_sorted = sorted(vector_results, key=lambda x: x.get("vector_score", 0), reverse=True)
    for rank, c in enumerate(vector_sorted, 1):
        cid = c["candidate_id"]
        rrf_scores[cid] = rrf_scores.get(cid, 0) + 1.0 / (k + rank)
        all_candidates[cid] = c

    bm25_sorted = sorted(bm25_results, key=lambda x: x.get("bm25_score", 0), reverse=True)
    for rank, c in enumerate(bm25_sorted, 1):
        cid = c["candidate_id"]
        rrf_scores[cid] = rrf_scores.get(cid, 0) + 1.0 / (k + rank)
        if cid not in all_candidates:
            all_candidates[cid] = c

    for cid, c in all_candidates.items():
        c["rrf_score"] = rrf_scores.get(cid, 0)

    merged = list(all_candidates.values())
    merged.sort(key=lambda x: x.get("rrf_score", 0), reverse=True)
    return merged


def hybrid_retrieve(query_text: str, parsed_jd: dict, exclude_rejected: bool = True, limit: int = 100) -> list[dict]:
    vector_results = vector_search(query_text, parsed_jd, exclude_rejected, limit)

    if not vector_results:
        return []

    bm25_results = bm25_search(query_text, list(vector_results), limit)
    merged = reciprocal_rank_fusion(vector_results, bm25_results)
    return merged[:limit]
