import uuid
import enum
from datetime import datetime, date
from sqlalchemy import (
    String, Text, Integer, Float, DateTime, Date, Enum,
    ForeignKey, ARRAY, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


class CandidateStatus(str, enum.Enum):
    new = "new"
    contacted = "contacted"
    shortlisted = "shortlisted"
    interview_scheduled = "interview_scheduled"
    rejected = "rejected"
    hired = "hired"


class SkillSource(str, enum.Enum):
    linkedin_skills_section = "linkedin_skills_section"
    inferred_from_experience = "inferred_from_experience"


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    linkedin_url: Mapped[str | None] = mapped_column(String(500), unique=True, nullable=True, index=True)
    full_name: Mapped[str] = mapped_column(String(300), nullable=False)
    headline: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(300), nullable=True)
    email: Mapped[str | None] = mapped_column(String(300), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_role: Mapped[str | None] = mapped_column(String(300), nullable=True)
    current_company: Mapped[str | None] = mapped_column(String(300), nullable=True)
    total_experience_months: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    candidate_status: Mapped[CandidateStatus] = mapped_column(
        Enum(CandidateStatus, name="candidate_status_enum", create_constraint=True),
        default=CandidateStatus.new, nullable=False, index=True
    )
    raw_extracted_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    source_pdf_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    experiences: Mapped[list["Experience"]] = relationship(back_populates="candidate", cascade="all, delete-orphan", order_by="Experience.display_order")
    education_entries: Mapped[list["Education"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    skills: Mapped[list["Skill"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    versions: Mapped[list["CandidateVersion"]] = relationship(back_populates="candidate", cascade="all, delete-orphan", order_by="CandidateVersion.version_number.desc()")
    notes: Mapped[list["CandidateNote"]] = relationship(back_populates="candidate", cascade="all, delete-orphan", order_by="CandidateNote.created_at.desc()")

    __table_args__ = (
        Index("ix_candidates_name_company", "full_name", "current_company"),
    )


class Experience(Base):
    __tablename__ = "experiences"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    company: Mapped[str | None] = mapped_column(String(300), nullable=True)
    role: Mapped[str | None] = mapped_column(String(300), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    candidate: Mapped["Candidate"] = relationship(back_populates="experiences")

    __table_args__ = (
        Index("ix_experiences_company", "candidate_id", "company"),
    )


class Education(Base):
    __tablename__ = "education"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    institution: Mapped[str | None] = mapped_column(String(500), nullable=True)
    degree: Mapped[str | None] = mapped_column(String(300), nullable=True)
    field: Mapped[str | None] = mapped_column(String(300), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    candidate: Mapped["Candidate"] = relationship(back_populates="education_entries")


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    original_skill: Mapped[str] = mapped_column(String(200), nullable=False)
    normalized_skills: Mapped[list[str] | None] = mapped_column(ARRAY(String(200)), nullable=True)
    source: Mapped[SkillSource] = mapped_column(
        Enum(SkillSource, name="skill_source_enum", create_constraint=True),
        default=SkillSource.linkedin_skills_section
    )

    candidate: Mapped["Candidate"] = relationship(back_populates="skills")

    __table_args__ = (
        Index("ix_skills_normalized", "normalized_skills", postgresql_using="gin"),
    )


class CandidateVersion(Base):
    __tablename__ = "candidate_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_profile_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    updated_profile_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    changes_summary: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    upload_source_pdf_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    candidate: Mapped["Candidate"] = relationship(back_populates="versions")


class CandidateNote(Base):
    __tablename__ = "candidate_notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    note_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    candidate: Mapped["Candidate"] = relationship(back_populates="notes")


class SearchLog(Base):
    __tablename__ = "search_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    jd_text: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_jd_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    result_candidate_ids: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
