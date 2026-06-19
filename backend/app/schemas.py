from pydantic import BaseModel, Field
from datetime import datetime, date
from uuid import UUID
from enum import Enum
from typing import Any


class CandidateStatusEnum(str, Enum):
    new = "new"
    contacted = "contacted"
    shortlisted = "shortlisted"
    interview_scheduled = "interview_scheduled"
    rejected = "rejected"
    hired = "hired"


# --- Auth ---
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Upload ---
class UploadResponse(BaseModel):
    batch_id: str
    files_received: int
    status: str = "processing"

class UploadFileStatus(BaseModel):
    filename: str
    status: str
    reason: str | None = None
    candidate_id: str | None = None
    is_update: bool = False

class BatchStatusResponse(BaseModel):
    batch_id: str
    total: int
    processed: int
    succeeded: int
    failed: int
    status: str
    files: list[UploadFileStatus] = []


# --- Experience ---
class ExperienceOut(BaseModel):
    id: UUID
    company: str | None = None
    role: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None
    display_order: int = 0

    model_config = {"from_attributes": True}


# --- Education ---
class EducationOut(BaseModel):
    id: UUID
    institution: str | None = None
    degree: str | None = None
    field: str | None = None
    start_date: date | None = None
    end_date: date | None = None

    model_config = {"from_attributes": True}


# --- Skills ---
class SkillOut(BaseModel):
    id: UUID
    original_skill: str
    normalized_skills: list[str] | None = None
    source: str

    model_config = {"from_attributes": True}


# --- Notes ---
class NoteOut(BaseModel):
    id: UUID
    note_text: str
    created_at: datetime

    model_config = {"from_attributes": True}

class NoteCreate(BaseModel):
    note_text: str


# --- Version ---
class VersionOut(BaseModel):
    version_number: int
    changes_summary: list[str] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Candidate ---
class CandidateSummary(BaseModel):
    id: UUID
    full_name: str
    headline: str | None = None
    location: str | None = None
    current_role: str | None = None
    current_company: str | None = None
    total_experience_months: int | None = 0
    candidate_status: CandidateStatusEnum
    extraction_confidence: float | None = None
    current_version: int = 1
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}

class CandidateDetail(BaseModel):
    id: UUID
    linkedin_url: str | None = None
    full_name: str
    headline: str | None = None
    location: str | None = None
    email: str | None = None
    phone: str | None = None
    summary: str | None = None
    current_role: str | None = None
    current_company: str | None = None
    total_experience_months: int | None = 0
    candidate_status: CandidateStatusEnum
    extraction_confidence: float | None = None
    current_version: int = 1
    source_pdf_path: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    experiences: list[ExperienceOut] = []
    education_entries: list[EducationOut] = []
    skills: list[SkillOut] = []
    notes: list[NoteOut] = []

    model_config = {"from_attributes": True}

class CandidateUpdate(BaseModel):
    full_name: str | None = None
    headline: str | None = None
    location: str | None = None
    email: str | None = None
    phone: str | None = None
    summary: str | None = None
    current_role: str | None = None
    current_company: str | None = None
    total_experience_months: int | None = None
    candidate_status: CandidateStatusEnum | None = None

class CandidateListResponse(BaseModel):
    candidates: list[CandidateSummary]
    total: int
    page: int
    page_size: int


# --- Search ---
class ScoreBreakdown(BaseModel):
    semantic: float = 0
    skill: float = 0
    role: float = 0
    experience: float = 0

class SearchResultCandidate(BaseModel):
    candidate_id: UUID
    full_name: str
    headline: str | None = None
    location: str | None = None
    current_role: str | None = None
    current_company: str | None = None
    total_experience_months: int | None = 0
    match_score: float
    score_breakdown: ScoreBreakdown
    match_explanation: list[str]
    extraction_confidence: float | None = None
    candidate_status: CandidateStatusEnum

class ParsedQuery(BaseModel):
    role: str | None = None
    required_skills: list[str] = []
    preferred_skills: list[str] = []
    experience: dict[str, int | None] = {}
    location: str | None = None
    industry: str | None = None

class SearchRequest(BaseModel):
    query: str
    filters: dict[str, Any] = {}
    limit: int = 20

class SearchResponse(BaseModel):
    parsed_query: ParsedQuery
    results: list[SearchResultCandidate]
    total_found: int


# --- Export ---
class ExportRequest(BaseModel):
    candidate_ids: list[UUID] | None = None
    filters: dict[str, str] | None = None
