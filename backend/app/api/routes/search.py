from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.api.deps import get_current_user
from app.schemas import SearchRequest, SearchResponse, SearchResultCandidate, ParsedQuery, ScoreBreakdown
from app.search.jd_parser import parse_jd
from app.search.retrieval import hybrid_retrieve
from app.search.reranker import rerank_candidates
from app.search.scorer import score_all_candidates
from app.search.explainer import add_explanations
from app.models import SearchLog
from app.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search_candidates(
    req: SearchRequest,
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    parsed_jd = await parse_jd(req.query)
    logger.info(f"Parsed JD: {parsed_jd}")

    exclude_rejected = req.filters.get("exclude_rejected", True)

    query_text = req.query
    if parsed_jd.get("role"):
        query_text = f"{parsed_jd['role']} {' '.join(parsed_jd.get('required_skills', []))} {' '.join(parsed_jd.get('preferred_skills', []))}"

    candidates = hybrid_retrieve(query_text, parsed_jd, exclude_rejected=exclude_rejected, limit=100)

    if candidates:
        candidates = rerank_candidates(req.query, candidates, top_n=settings.RERANK_TOP_N)

    candidates = score_all_candidates(candidates, parsed_jd)
    candidates = add_explanations(candidates, parsed_jd)

    top_results = candidates[:req.limit]

    results = []
    for c in top_results:
        payload = c.get("payload", {})
        cid = payload.get("candidate_id")
        if not cid:
            continue
        results.append(SearchResultCandidate(
            candidate_id=cid,
            full_name=payload.get("full_name", "Unknown"),
            headline=payload.get("headline"),
            location=payload.get("location"),
            current_role=payload.get("current_role"),
            current_company=payload.get("current_company"),
            total_experience_months=payload.get("total_experience_months", 0),
            match_score=c.get("match_score", 0),
            score_breakdown=ScoreBreakdown(**c.get("score_breakdown", {})),
            match_explanation=c.get("match_explanation", []),
            extraction_confidence=payload.get("extraction_confidence"),
            candidate_status=payload.get("candidate_status", "new"),
        ))

    search_log = SearchLog(
        jd_text=req.query,
        parsed_jd_json=parsed_jd,
        result_candidate_ids=[str(r.candidate_id) for r in results],
    )
    db.add(search_log)

    return SearchResponse(
        parsed_query=ParsedQuery(**parsed_jd),
        results=results,
        total_found=len(results),
    )
