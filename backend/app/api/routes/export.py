import io
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd
from datetime import datetime

from app.db import get_db
from app.api.deps import get_current_user
from app.models import Candidate
from app.schemas import ExportRequest

router = APIRouter()


@router.post("/candidates/export")
async def export_candidates(
    req: ExportRequest,
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    stmt = (
        select(Candidate)
        .options(selectinload(Candidate.skills))
        .where(Candidate.deleted_at.is_(None))
    )

    if req.candidate_ids:
        stmt = stmt.where(Candidate.id.in_(req.candidate_ids))
    elif req.filters:
        if "status" in req.filters:
            stmt = stmt.where(Candidate.candidate_status == req.filters["status"])
        if "location" in req.filters:
            stmt = stmt.where(Candidate.location.ilike(f"%{req.filters['location']}%"))

    result = await db.execute(stmt)
    candidates = result.scalars().all()

    if not candidates:
        raise HTTPException(status_code=404, detail="No candidates found for export")

    rows = []
    for c in candidates:
        all_skills = []
        for s in c.skills:
            all_skills.extend(s.normalized_skills or [s.original_skill])

        rows.append({
            "Name": c.full_name,
            "Headline": c.headline or "",
            "Location": c.location or "",
            "Email": c.email or "",
            "Phone": c.phone or "",
            "Current Role": c.current_role or "",
            "Current Company": c.current_company or "",
            "Total Experience (months)": c.total_experience_months or 0,
            "Status": c.candidate_status.value,
            "Skills": ", ".join(set(all_skills)),
            "LinkedIn URL": c.linkedin_url or "",
        })

    df = pd.DataFrame(rows)
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)

    today = datetime.now().strftime("%Y-%m-%d")
    return StreamingResponse(
        io.BytesIO(buffer.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=candidates-{today}.csv"},
    )
