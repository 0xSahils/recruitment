import uuid
import shutil
from datetime import datetime
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.config import PDF_STORAGE
from app.models import (
    Candidate, Experience, Education, Skill, CandidateVersion, CandidateNote, SkillSource
)
from app.pdf.extractor import extract_text_from_bytes
from app.llm.client import generate
from app.llm.prompts import RESUME_PARSE_SYSTEM, RESUME_PARSE_PROMPT
from app.llm.parsers import safe_parse_json, validate_resume_json
from app.parsing.linkedin_parser import parse_linkedin_pdf
from app.parsing.validators import sanitize_parsed_data, parse_date, compute_experience_months
from app.skills.normalizer import normalize_skills, get_all_normalized_skills
from app.identity.resolver import find_existing_candidate, normalize_linkedin_url
from app.identity.differ import generate_changes_summary
from app.embeddings.generator import compose_candidate_text, generate_embedding
from app.vector_db import upsert_candidate_vector
import logging

logger = logging.getLogger(__name__)


def _extract_education_keywords(parsed: dict) -> list[str]:
    keywords = []
    for edu in parsed.get("education", []):
        degree = (edu.get("degree") or "").lower()
        field = (edu.get("field") or "").lower()
        for term in ["mba", "btech", "b.tech", "mtech", "m.tech", "phd", "mca", "bca", "msc", "bsc", "bba", "pgdm"]:
            if term in degree:
                keywords.append(term)
        if field:
            keywords.append(field)
    return list(set(keywords))


def _candidate_to_profile_dict(candidate: Candidate) -> dict:
    return {
        "identity": {
            "linkedin_url": candidate.linkedin_url,
            "full_name": candidate.full_name,
            "headline": candidate.headline,
            "location": candidate.location,
            "email": candidate.email,
            "phone": candidate.phone,
        },
        "summary": candidate.summary,
        "experience": [
            {
                "company": e.company,
                "role": e.role,
                "start_date": str(e.start_date) if e.start_date else None,
                "end_date": str(e.end_date) if e.end_date else None,
                "description": e.description,
            }
            for e in (candidate.experiences or [])
        ],
        "education": [
            {
                "institution": ed.institution,
                "degree": ed.degree,
                "field": ed.field,
                "start_date": str(ed.start_date) if ed.start_date else None,
                "end_date": str(ed.end_date) if ed.end_date else None,
            }
            for ed in (candidate.education_entries or [])
        ],
        "skills": {
            "original": [s.original_skill for s in (candidate.skills or [])],
            "normalized": list(
                set(
                    n
                    for s in (candidate.skills or [])
                    for n in (s.normalized_skills or [])
                )
            ),
        },
        "total_experience_months": candidate.total_experience_months,
    }


async def process_single_pdf(
    session: AsyncSession,
    pdf_bytes: bytes,
    filename: str,
) -> dict:
    result = {"filename": filename, "status": "failed", "reason": None, "candidate_id": None, "is_update": False}

    try:
        raw_text = extract_text_from_bytes(pdf_bytes, filename)
    except ValueError as e:
        result["reason"] = str(e)
        return result

    # Try rule-based LinkedIn parser first (fast + accurate)
    parsed = parse_linkedin_pdf(raw_text, pdf_bytes=pdf_bytes)
    if parsed:
        logger.info(f"{filename}: Using rule-based parser")
    else:
        # Fallback to LLM for non-LinkedIn PDFs
        logger.info(f"{filename}: Rule-based parse failed, falling back to LLM")
        prompt = RESUME_PARSE_PROMPT.format(resume_text=raw_text[:6000])
        try:
            llm_output = await generate(prompt, system=RESUME_PARSE_SYSTEM)
        except Exception as e:
            result["reason"] = f"LLM parsing failed: {e}"
            return result

        parsed = safe_parse_json(llm_output)
        if not isinstance(parsed, dict):
            result["reason"] = "Failed to parse LLM JSON output"
            return result

    parsed = sanitize_parsed_data(parsed)
    parsed, confidence = validate_resume_json(parsed)

    if confidence == 0:
        result["reason"] = "Extraction confidence too low — no name found"
        return result

    identity = parsed.get("identity", {})

    if not identity.get("headline"):
        exp_list_temp = parsed.get("experience", [])
        if exp_list_temp:
            role = exp_list_temp[0].get("role", "")
            company = exp_list_temp[0].get("company", "")
            if role and company:
                identity["headline"] = f"{role} at {company}"
            elif role:
                identity["headline"] = role

    pdf_filename = f"{uuid.uuid4().hex}_{filename}"
    pdf_path = PDF_STORAGE / pdf_filename
    pdf_path.write_bytes(pdf_bytes)

    exp_list = parsed.get("experience", [])
    if exp_list:
        identity["company"] = exp_list[0].get("company", "")

    existing = await find_existing_candidate(session, identity)

    if existing:
        stmt = select(Candidate).options(
            selectinload(Candidate.experiences),
            selectinload(Candidate.education_entries),
            selectinload(Candidate.skills),
        ).where(Candidate.id == existing.id)
        res = await session.execute(stmt)
        candidate = res.scalar_one()

        old_profile = _candidate_to_profile_dict(candidate)
        changes = generate_changes_summary(old_profile, parsed)

        new_version = candidate.current_version + 1
        version_record = CandidateVersion(
            candidate_id=candidate.id,
            version_number=new_version,
            previous_profile_json=old_profile,
            updated_profile_json=parsed,
            changes_summary=changes,
            upload_source_pdf_path=str(pdf_path),
        )
        session.add(version_record)

        candidate.full_name = identity.get("full_name", candidate.full_name)
        candidate.headline = identity.get("headline") or candidate.headline
        candidate.location = identity.get("location") or candidate.location
        candidate.email = identity.get("email") or candidate.email
        candidate.phone = identity.get("phone") or candidate.phone
        candidate.linkedin_url = normalize_linkedin_url(identity.get("linkedin_url")) or candidate.linkedin_url
        candidate.summary = parsed.get("summary") or candidate.summary
        candidate.raw_extracted_json = parsed
        candidate.source_pdf_path = str(pdf_path)
        candidate.extraction_confidence = confidence
        candidate.current_version = new_version
        candidate.updated_at = datetime.utcnow()
        candidate.deleted_at = None  # Restore candidate if they were soft-deleted

        exp = parsed.get("experience", [])
        if exp:
            candidate.total_experience_months = compute_experience_months(exp)
            candidate.current_role = exp[0].get("role")
            candidate.current_company = exp[0].get("company")

        for e in list(candidate.experiences):
            await session.delete(e)
        for i, exp_data in enumerate(parsed.get("experience", [])):
            session.add(Experience(
                candidate_id=candidate.id,
                company=exp_data.get("company"),
                role=exp_data.get("role"),
                start_date=parse_date(exp_data.get("start_date")),
                end_date=parse_date(exp_data.get("end_date")),
                description=exp_data.get("description"),
                display_order=i,
            ))

        for ed in list(candidate.education_entries):
            await session.delete(ed)
        for edu_data in parsed.get("education", []):
            session.add(Education(
                candidate_id=candidate.id,
                institution=edu_data.get("institution"),
                degree=edu_data.get("degree"),
                field=edu_data.get("field"),
                start_date=parse_date(edu_data.get("start_date")),
                end_date=parse_date(edu_data.get("end_date")),
            ))

        for sk in list(candidate.skills):
            await session.delete(sk)
        original_skills = parsed.get("skills", {}).get("original", [])
        all_normalized = get_all_normalized_skills(parsed)
        for orig in original_skills:
            session.add(Skill(
                candidate_id=candidate.id,
                original_skill=orig,
                normalized_skills=normalize_skills([orig]),
                source=SkillSource.linkedin_skills_section,
            ))

        await session.flush()

        candidate_text = compose_candidate_text(parsed)
        embedding = generate_embedding(candidate_text)
        metadata = {
            "candidate_id": str(candidate.id),
            "location": candidate.location or "",
            "total_experience_months": candidate.total_experience_months or 0,
            "candidate_status": candidate.candidate_status.value,
            "normalized_skills": all_normalized,
            "full_name": candidate.full_name,
            "headline": candidate.headline or "",
            "current_role": candidate.current_role or "",
            "current_company": candidate.current_company or "",
            "profile_text": candidate_text[:8000],
            "extraction_confidence": confidence,
            "education_keywords": _extract_education_keywords(parsed),
        }
        upsert_candidate_vector(str(candidate.id), embedding, metadata)

        result["status"] = "success"
        result["candidate_id"] = str(candidate.id)
        result["is_update"] = True
        return result

    else:
        candidate_id = uuid.uuid4()
        exp_data = parsed.get("experience", [])
        total_months = compute_experience_months(exp_data)
        current_role = exp_data[0].get("role") if exp_data else None
        current_company = exp_data[0].get("company") if exp_data else None

        candidate = Candidate(
            id=candidate_id,
            linkedin_url=normalize_linkedin_url(identity.get("linkedin_url")),
            full_name=identity.get("full_name", "Unknown"),
            headline=identity.get("headline"),
            location=identity.get("location"),
            email=identity.get("email"),
            phone=identity.get("phone"),
            summary=parsed.get("summary"),
            current_role=current_role,
            current_company=current_company,
            total_experience_months=total_months,
            raw_extracted_json=parsed,
            source_pdf_path=str(pdf_path),
            extraction_confidence=confidence,
        )
        session.add(candidate)

        for i, exp in enumerate(exp_data):
            session.add(Experience(
                candidate_id=candidate_id,
                company=exp.get("company"),
                role=exp.get("role"),
                start_date=parse_date(exp.get("start_date")),
                end_date=parse_date(exp.get("end_date")),
                description=exp.get("description"),
                display_order=i,
            ))

        for edu in parsed.get("education", []):
            session.add(Education(
                candidate_id=candidate_id,
                institution=edu.get("institution"),
                degree=edu.get("degree"),
                field=edu.get("field"),
                start_date=parse_date(edu.get("start_date")),
                end_date=parse_date(edu.get("end_date")),
            ))

        original_skills = parsed.get("skills", {}).get("original", [])
        all_normalized = get_all_normalized_skills(parsed)
        for orig in original_skills:
            session.add(Skill(
                candidate_id=candidate_id,
                original_skill=orig,
                normalized_skills=normalize_skills([orig]),
                source=SkillSource.linkedin_skills_section,
            ))

        version_record = CandidateVersion(
            candidate_id=candidate_id,
            version_number=1,
            previous_profile_json=None,
            updated_profile_json=parsed,
            changes_summary=["Initial profile creation"],
            upload_source_pdf_path=str(pdf_path),
        )
        session.add(version_record)

        await session.flush()

        candidate_text = compose_candidate_text(parsed)
        embedding = generate_embedding(candidate_text)
        metadata = {
            "candidate_id": str(candidate_id),
            "location": identity.get("location", ""),
            "total_experience_months": total_months,
            "candidate_status": "new",
            "normalized_skills": all_normalized,
            "full_name": identity.get("full_name", ""),
            "headline": identity.get("headline", ""),
            "current_role": current_role or "",
            "current_company": current_company or "",
            "profile_text": candidate_text[:8000],
            "extraction_confidence": confidence,
            "education_keywords": _extract_education_keywords(parsed),
        }
        upsert_candidate_vector(str(candidate_id), embedding, metadata)

        result["status"] = "success"
        result["candidate_id"] = str(candidate_id)
        result["is_update"] = False
        return result
