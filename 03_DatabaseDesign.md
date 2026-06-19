# Database Design Document

## Design Principle — Future-Proof Extraction
Never store only a flattened summary. Always store every structured field separately (one row per experience entry, one row per education entry) AND store the complete raw extracted JSON plus the original PDF file path. This allows re-running a better parser in the future without asking recruiters to re-upload anything, and enables filters like "worked at WheelsEye" or "experience > 2 years" without re-parsing.

---

## Core Entities

### `candidates`
Primary entity. One row per unique person (see Identity Resolution in `04_AIMatchingSpec.md` for what makes a candidate "unique").

| Field | Type | Notes |
|---|---|---|
| id | UUID, PK | |
| linkedin_url | TEXT, UNIQUE, nullable | Primary identity key when present |
| full_name | TEXT | |
| headline | TEXT | e.g. "Software Engineer @ WheelsEye" |
| location | TEXT | |
| email | TEXT, nullable | |
| phone | TEXT, nullable | |
| summary | TEXT | "About" section |
| current_role | TEXT | Derived from most recent experience entry |
| current_company | TEXT | Derived from most recent experience entry |
| total_experience_months | INTEGER | Computed from experience entries |
| candidate_status | ENUM | `new`, `contacted`, `interview_scheduled`, `rejected`, `hired` |
| notes | TEXT | Recruiter free-text notes |
| raw_extracted_json | JSONB | Full LLM extraction output, unmodified — future-proofing |
| source_pdf_path | TEXT | Path to original uploaded PDF, always retained |
| extraction_confidence | FLOAT, nullable | 0–1 score from parsing step; low scores flagged for recruiter review (see `04_AIMatchingSpec.md`) |
| current_version | INTEGER | Increments on each re-upload update |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |

---

### `experiences`
One-to-many with `candidates`.

| Field | Type | Notes |
|---|---|---|
| id | UUID, PK | |
| candidate_id | UUID, FK → candidates.id | |
| company | TEXT | |
| role | TEXT | |
| start_date | DATE, nullable | LinkedIn often gives month/year only — store as first-of-month |
| end_date | DATE, nullable | NULL = current role |
| description | TEXT | |
| display_order | INTEGER | Preserves original PDF ordering |

---

### `education`
One-to-many with `candidates`.

| Field | Type | Notes |
|---|---|---|
| id | UUID, PK | |
| candidate_id | UUID, FK → candidates.id | |
| institution | TEXT | |
| degree | TEXT | |
| field | TEXT | |
| start_date | DATE, nullable | |
| end_date | DATE, nullable | |

---

### `skills`
Stores both the original (as written by candidate) and normalized form.

| Field | Type | Notes |
|---|---|---|
| id | UUID, PK | |
| candidate_id | UUID, FK → candidates.id | |
| original_skill | TEXT | e.g. "MERN" |
| normalized_skills | TEXT[] | e.g. `['React', 'Node.js', 'MongoDB', 'Express.js']` — see normalization rules in `04_AIMatchingSpec.md` |
| source | ENUM | `linkedin_skills_section`, `inferred_from_experience` |

---

### `candidate_versions`
Tracks every re-upload. Critical client-facing feature — shows "what changed" instead of silently overwriting.

| Field | Type | Notes |
|---|---|---|
| id | UUID, PK | |
| candidate_id | UUID, FK → candidates.id | |
| version_number | INTEGER | |
| previous_profile_json | JSONB | Full snapshot before this update |
| updated_profile_json | JSONB | Full snapshot after this update |
| changes_summary | TEXT[] | Human-readable diff, e.g. `["Added Software Engineer role", "Added AWS skill", "Updated location"]` |
| upload_source_pdf_path | TEXT | The PDF that triggered this version |
| created_at | TIMESTAMP | |

---

### `candidate_notes`
Separated from the `candidates.notes` field if multiple timestamped notes are needed (recommended over a single text blob, so history isn't lost on overwrite).

| Field | Type | Notes |
|---|---|---|
| id | UUID, PK | |
| candidate_id | UUID, FK → candidates.id | |
| note_text | TEXT | |
| created_at | TIMESTAMP | |

---

### `search_logs` (recommended addition — not in original draft)
Tracks every JD search run. Useful for: debugging bad matches, showing recruiters their search history, and future analytics on which JDs find candidates vs come up empty.

| Field | Type | Notes |
|---|---|---|
| id | UUID, PK | |
| jd_text | TEXT | Raw pasted JD |
| parsed_jd_json | JSONB | Structured JD (role, required_skills, preferred_skills, experience, location) |
| result_candidate_ids | UUID[] | Top N candidates returned, in rank order |
| created_at | TIMESTAMP | |

---

## Indexing Strategy
- `candidates.linkedin_url` — unique index (identity resolution)
- `candidates.email`, `candidates.phone` — indexes (identity resolution fallback)
- `candidates.candidate_status` — index (filter by pipeline stage)
- `experiences.company`, `experiences.candidate_id` — composite index (filter "worked at X")
- `skills.normalized_skills` — GIN index (array containment queries, e.g. "has React")

## Vector Store (Qdrant) — Companion to PostgreSQL
Each candidate has one or more vector points in Qdrant:
- A primary embedding of the full canonical profile text (see `04_AIMatchingSpec.md` for canonical profile structure)
- Metadata payload attached to each vector: `candidate_id`, `location`, `total_experience_months`, `candidate_status`, `normalized_skills` — enables Stage 1 metadata filtering before vector search runs

On every candidate update (manual edit or re-upload), the corresponding Qdrant vector and metadata payload must be recomputed and overwritten — never left stale.
