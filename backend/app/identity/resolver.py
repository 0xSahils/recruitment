import re
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from thefuzz import fuzz
from app.models import Candidate
import logging

logger = logging.getLogger(__name__)


def normalize_linkedin_url(url: str | None) -> str | None:
    if not url:
        return None
    url = url.strip().rstrip("/").lower()
    url = re.sub(r"https?://(www\.)?", "", url)
    if url.startswith("linkedin.com/in/"):
        return url
    return None


def normalize_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    return re.sub(r"[^\d+]", "", phone.strip())


async def find_existing_candidate(
    session: AsyncSession,
    identity: dict,
) -> Candidate | None:
    linkedin_url = normalize_linkedin_url(identity.get("linkedin_url"))
    if linkedin_url:
        stmt = select(Candidate).where(
            func.lower(Candidate.linkedin_url) == linkedin_url
        )
        result = await session.execute(stmt)
        candidate = result.scalar_one_or_none()
        if candidate:
            logger.info(f"Matched by LinkedIn URL: {linkedin_url}")
            return candidate

    email = identity.get("email")
    if email:
        stmt = select(Candidate).where(
            func.lower(Candidate.email) == email.lower().strip()
        )
        result = await session.execute(stmt)
        candidate = result.scalar_one_or_none()
        if candidate:
            logger.info(f"Matched by email: {email}")
            return candidate

    phone = normalize_phone(identity.get("phone"))
    if phone and len(phone) >= 7:
        stmt = select(Candidate)
        result = await session.execute(stmt)
        candidates = result.scalars().all()
        for c in candidates:
            if normalize_phone(c.phone) == phone:
                logger.info(f"Matched by phone: {phone}")
                return c

    full_name = identity.get("full_name", "").strip()
    if full_name and full_name.lower() != "unknown":
        stmt = select(Candidate)
        result = await session.execute(stmt)
        candidates = result.scalars().all()
        for c in candidates:
            name_score = fuzz.ratio(full_name.lower(), (c.full_name or "").lower())
            if name_score >= 95:
                logger.info(f"Matched by exact name: {full_name} (score={name_score})")
                return c
            if name_score >= 85:
                company = identity.get("company") or ""
                if company and c.current_company:
                    company_score = fuzz.ratio(company.lower(), c.current_company.lower())
                    if company_score >= 75:
                        logger.info(f"Matched by name+company: {full_name} / {company}")
                        return c

    return None
