from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.api.deps import get_current_user
from app.models import Candidate, CandidateNote, CandidateStatus
from app.schemas import (
    CandidateSummary, CandidateDetail, CandidateUpdate,
    CandidateListResponse, NoteCreate, NoteOut, VersionOut,
)
from app.embeddings.generator import compose_candidate_text, generate_embedding
from app.vector_db import upsert_candidate_vector, delete_candidate_vector
from app.skills.normalizer import get_all_normalized_skills

router = APIRouter()

EMBEDDING_TRIGGER_FIELDS = {"summary", "headline", "current_role", "current_company", "location"}


@router.get("/candidates", response_model=CandidateListResponse)
async def list_candidates(
    status: str | None = None,
    location: str | None = None,
    skill: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    stmt = select(Candidate).where(Candidate.deleted_at.is_(None))

    if status:
        stmt = stmt.where(Candidate.candidate_status == status)
    if location:
        stmt = stmt.where(Candidate.location.ilike(f"%{location}%"))
    if search:
        stmt = stmt.where(
            Candidate.full_name.ilike(f"%{search}%") |
            Candidate.headline.ilike(f"%{search}%") |
            Candidate.current_role.ilike(f"%{search}%") |
            Candidate.current_company.ilike(f"%{search}%")
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    stmt = stmt.order_by(Candidate.updated_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    candidates = result.scalars().all()

    return CandidateListResponse(
        candidates=[CandidateSummary.model_validate(c) for c in candidates],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/candidates/{candidate_id}", response_model=CandidateDetail)
async def get_candidate(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    stmt = (
        select(Candidate)
        .options(
            selectinload(Candidate.experiences),
            selectinload(Candidate.education_entries),
            selectinload(Candidate.skills),
            selectinload(Candidate.notes),
        )
        .where(and_(Candidate.id == candidate_id, Candidate.deleted_at.is_(None)))
    )
    result = await db.execute(stmt)
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    return CandidateDetail.model_validate(candidate)


@router.patch("/candidates/{candidate_id}", response_model=CandidateDetail)
async def update_candidate(
    candidate_id: UUID,
    update: CandidateUpdate,
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    stmt = (
        select(Candidate)
        .options(
            selectinload(Candidate.experiences),
            selectinload(Candidate.education_entries),
            selectinload(Candidate.skills),
            selectinload(Candidate.notes),
        )
        .where(and_(Candidate.id == candidate_id, Candidate.deleted_at.is_(None)))
    )
    result = await db.execute(stmt)
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    update_data = update.model_dump(exclude_unset=True)
    needs_reembed = False
    for field, value in update_data.items():
        setattr(candidate, field, value)
        if field in EMBEDDING_TRIGGER_FIELDS:
            needs_reembed = True

    candidate.updated_at = datetime.utcnow()
    await db.flush()

    if needs_reembed:
        profile_data = candidate.raw_extracted_json or {}
        identity = profile_data.get("identity", {})
        identity["full_name"] = candidate.full_name
        identity["headline"] = candidate.headline
        identity["location"] = candidate.location
        profile_data["identity"] = identity
        profile_data["summary"] = candidate.summary

        candidate_text = compose_candidate_text(profile_data)
        embedding = generate_embedding(candidate_text)
        all_normalized = [n for s in candidate.skills for n in (s.normalized_skills or [])]
        metadata = {
            "candidate_id": str(candidate.id),
            "location": candidate.location or "",
            "total_experience_months": candidate.total_experience_months or 0,
            "candidate_status": candidate.candidate_status.value,
            "normalized_skills": list(set(all_normalized)),
            "full_name": candidate.full_name,
            "headline": candidate.headline or "",
            "current_role": candidate.current_role or "",
            "current_company": candidate.current_company or "",
            "profile_text": candidate_text[:1000],
        }
        upsert_candidate_vector(str(candidate.id), embedding, metadata)

    return CandidateDetail.model_validate(candidate)


@router.delete("/candidates/{candidate_id}")
async def delete_candidate(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    stmt = select(Candidate).where(and_(Candidate.id == candidate_id, Candidate.deleted_at.is_(None)))
    result = await db.execute(stmt)
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    candidate.deleted_at = datetime.utcnow()
    try:
        delete_candidate_vector(str(candidate_id))
    except Exception:
        pass
    return {"message": "Candidate deleted"}


@router.post("/candidates/{candidate_id}/notes", response_model=NoteOut)
async def add_note(
    candidate_id: UUID,
    note: NoteCreate,
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    stmt = select(Candidate).where(and_(Candidate.id == candidate_id, Candidate.deleted_at.is_(None)))
    result = await db.execute(stmt)
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    new_note = CandidateNote(candidate_id=candidate_id, note_text=note.note_text)
    db.add(new_note)
    await db.flush()
    return NoteOut.model_validate(new_note)


@router.get("/candidates/{candidate_id}/versions", response_model=dict)
async def get_versions(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    stmt = (
        select(Candidate)
        .options(selectinload(Candidate.versions))
        .where(and_(Candidate.id == candidate_id, Candidate.deleted_at.is_(None)))
    )
    result = await db.execute(stmt)
    candidate = result.scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    return {"versions": [VersionOut.model_validate(v) for v in candidate.versions]}
