# API Contracts Document
All endpoints are REST, JSON request/response. Base path: `/api/v1`

---

## Upload

### `POST /api/v1/candidates/upload`
Bulk upload LinkedIn PDFs.

**Request:** `multipart/form-data`, field name `files`, accepts multiple files.

**Response (202 Accepted — processing is async):**
```json
{
  "batch_id": "uuid",
  "files_received": 100,
  "status": "processing"
}
```

### `GET /api/v1/candidates/upload/{batch_id}/status`
Poll for batch processing progress.

**Response:**
```json
{
  "batch_id": "uuid",
  "total": 100,
  "processed": 67,
  "succeeded": 64,
  "failed": 3,
  "status": "processing",
  "failures": [
    { "filename": "broken.pdf", "reason": "No text layer found — possibly scanned image" }
  ]
}
```
`status` values: `processing`, `completed`, `completed_with_errors`

---

## Search

### `POST /api/v1/search`
Run a JD or natural-language search against the candidate pool.

**Request:**
```json
{
  "query": "React developers in Bangalore with AWS and 5+ years",
  "filters": {
    "exclude_rejected": true
  },
  "limit": 20
}
```

**Response:**
```json
{
  "parsed_query": {
    "role": "React Developer",
    "required_skills": ["React"],
    "preferred_skills": ["AWS"],
    "experience": { "min_years": 5, "max_years": null },
    "location": "Bangalore"
  },
  "results": [
    {
      "candidate_id": "uuid",
      "full_name": "Priyanshu Bansal",
      "headline": "Software Engineer @ WheelsEye",
      "location": "Gurugram, Haryana, India",
      "match_score": 87,
      "score_breakdown": {
        "semantic": 44,
        "skill": 22,
        "role": 12,
        "experience": 9
      },
      "match_explanation": [
        "Has React and AWS in normalized skills",
        "3 years as Software Engineer — close match to required role",
        "5.5 years total experience meets the 5+ year requirement"
      ],
      "extraction_confidence": 0.92,
      "candidate_status": "new"
    }
  ],
  "total_found": 14
}
```

---

## Candidates — CRUD

### `GET /api/v1/candidates`
List/filter candidates (paginated).

**Query params:** `status`, `location`, `skill`, `page`, `page_size`

**Response:**
```json
{
  "candidates": [ /* array of candidate summary objects, same shape as search results minus match fields */ ],
  "total": 412,
  "page": 1,
  "page_size": 50
}
```

### `GET /api/v1/candidates/{candidate_id}`
Full candidate profile.

**Response:**
```json
{
  "id": "uuid",
  "identity": { "linkedin_url": "...", "full_name": "...", "headline": "...", "location": "...", "email": null, "phone": null },
  "summary": "...",
  "experience": [ { "company": "...", "role": "...", "start_date": "...", "end_date": null, "description": "..." } ],
  "education": [ { "institution": "...", "degree": "...", "field": "...", "start_date": "...", "end_date": "..." } ],
  "skills": { "original": ["MERN"], "normalized": ["React", "Node.js", "MongoDB", "Express.js"] },
  "total_experience_months": 18,
  "candidate_status": "new",
  "notes": [ { "id": "uuid", "note_text": "Called 15 June, interested", "created_at": "..." } ],
  "extraction_confidence": 0.92,
  "current_version": 2,
  "source_pdf_path": "/storage/pdfs/priyanshu_bansal_v2.pdf",
  "created_at": "...",
  "updated_at": "..."
}
```

### `PATCH /api/v1/candidates/{candidate_id}`
Edit any candidate field. Partial update — only send changed fields.

**Request example:**
```json
{
  "candidate_status": "shortlisted",
  "headline": "Senior Software Engineer @ WheelsEye"
}
```

**Response:** Updated full candidate object (same shape as GET above). Note: editing fields used in embeddings (summary, experience, skills, headline) must trigger Qdrant vector recomputation server-side — not exposed to frontend, but must happen.

### `POST /api/v1/candidates/{candidate_id}/notes`
Add a note (does not overwrite previous notes).

**Request:**
```json
{ "note_text": "Called 15 June, interested, salary expectation ₹18L" }
```

### `GET /api/v1/candidates/{candidate_id}/versions`
Version history.

**Response:**
```json
{
  "versions": [
    {
      "version_number": 2,
      "changes_summary": ["Added Software Engineer role", "Added AWS skill", "Updated location"],
      "created_at": "2026-08-12T..."
    },
    {
      "version_number": 1,
      "changes_summary": ["Initial profile creation"],
      "created_at": "2026-06-01T..."
    }
  ]
}
```

### `DELETE /api/v1/candidates/{candidate_id}`
Soft delete recommended (add `deleted_at` column) rather than hard delete — recruiters may need to recover accidental deletions. Not in original schema — flag as an addition if implementing.

---

## Export

### `POST /api/v1/candidates/export`
Export filtered candidates as CSV.

**Request:**
```json
{ "candidate_ids": ["uuid1", "uuid2"] }
```
or
```json
{ "filters": { "status": "shortlisted" } }
```

**Response:** `text/csv` file stream, `Content-Disposition: attachment; filename=shortlist-2026-06-19.csv`

---

## Error Format (all endpoints)
```json
{
  "error": {
    "code": "CANDIDATE_NOT_FOUND",
    "message": "No candidate found with id uuid",
    "details": null
  }
}
```
