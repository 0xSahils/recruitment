"""init schema

Revision ID: 001
Revises:
Create Date: 2026-06-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")

    candidate_status = sa.Enum(
        "new", "contacted", "shortlisted", "interview_scheduled", "rejected", "hired",
        name="candidate_status_enum"
    )
    candidate_status.create(op.get_bind(), checkfirst=True)

    skill_source = sa.Enum("linkedin_skills_section", "inferred_from_experience", name="skill_source_enum")
    skill_source.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "candidates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("linkedin_url", sa.String(500), unique=True, nullable=True),
        sa.Column("full_name", sa.String(300), nullable=False),
        sa.Column("headline", sa.Text, nullable=True),
        sa.Column("location", sa.String(300), nullable=True),
        sa.Column("email", sa.String(300), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("current_role", sa.String(300), nullable=True),
        sa.Column("current_company", sa.String(300), nullable=True),
        sa.Column("total_experience_months", sa.Integer, nullable=True, server_default="0"),
        sa.Column("candidate_status", candidate_status, nullable=False, server_default="new"),
        sa.Column("raw_extracted_json", JSONB, nullable=True),
        sa.Column("source_pdf_path", sa.Text, nullable=True),
        sa.Column("extraction_confidence", sa.Float, nullable=True),
        sa.Column("current_version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_candidates_linkedin_url", "candidates", ["linkedin_url"], unique=True)
    op.create_index("ix_candidates_email", "candidates", ["email"])
    op.create_index("ix_candidates_phone", "candidates", ["phone"])
    op.create_index("ix_candidates_status", "candidates", ["candidate_status"])
    op.create_index("ix_candidates_name_company", "candidates", ["full_name", "current_company"])

    op.create_table(
        "experiences",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("candidate_id", UUID(as_uuid=True), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company", sa.String(300), nullable=True),
        sa.Column("role", sa.String(300), nullable=True),
        sa.Column("start_date", sa.Date, nullable=True),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("display_order", sa.Integer, server_default="0"),
    )
    op.create_index("ix_experiences_company", "experiences", ["candidate_id", "company"])

    op.create_table(
        "education",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("candidate_id", UUID(as_uuid=True), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("institution", sa.String(500), nullable=True),
        sa.Column("degree", sa.String(300), nullable=True),
        sa.Column("field", sa.String(300), nullable=True),
        sa.Column("start_date", sa.Date, nullable=True),
        sa.Column("end_date", sa.Date, nullable=True),
    )

    op.create_table(
        "skills",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("candidate_id", UUID(as_uuid=True), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_skill", sa.String(200), nullable=False),
        sa.Column("normalized_skills", ARRAY(sa.String(200)), nullable=True),
        sa.Column("source", skill_source, nullable=False, server_default="linkedin_skills_section"),
    )
    op.create_index("ix_skills_normalized", "skills", ["normalized_skills"], postgresql_using="gin")

    op.create_table(
        "candidate_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("candidate_id", UUID(as_uuid=True), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("previous_profile_json", JSONB, nullable=True),
        sa.Column("updated_profile_json", JSONB, nullable=True),
        sa.Column("changes_summary", ARRAY(sa.Text), nullable=True),
        sa.Column("upload_source_pdf_path", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "candidate_notes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("candidate_id", UUID(as_uuid=True), sa.ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("note_text", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "search_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("jd_text", sa.Text, nullable=False),
        sa.Column("parsed_jd_json", JSONB, nullable=True),
        sa.Column("result_candidate_ids", ARRAY(sa.String), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("search_logs")
    op.drop_table("candidate_notes")
    op.drop_table("candidate_versions")
    op.drop_table("skills")
    op.drop_table("education")
    op.drop_table("experiences")
    op.drop_table("candidates")
    op.execute("DROP TYPE IF EXISTS candidate_status_enum")
    op.execute("DROP TYPE IF EXISTS skill_source_enum")
