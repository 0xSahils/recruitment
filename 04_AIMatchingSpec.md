# AI Matching & Parsing Specification
This is the most important document in the set. Architectural decisions here directly determine match quality and parsing reliability.

---

## Part 1 — Resume Parsing

### Requirement
Extract ALL available information from a LinkedIn PDF export. Nothing is discarded — even sections not explicitly listed below should be captured into `raw_extracted_json` (see `03_DatabaseDesign.md`).

### Known LinkedIn PDF Sections
- Name
- Headline
- Location
- LinkedIn URL
- Summary / About
- Skills (a "Top Skills" section, when present, plus skills mentioned in experience descriptions)
- Experience (Company, Role, Start Date, End Date, Duration, Description) — per entry
- Education (Institute, Degree, Field, Dates) — per entry
- Certifications
- Projects
- Publications
- Languages
- Awards
- Contact Information

### Parsing Pipeline
```
PDF file
  ↓
PyMuPDF — extract raw text + layout structure
  ↓
Local LLM (Qwen2.5 via Ollama) — prompted to convert raw text into structured JSON
  matching the Candidate Canonical Profile shape below
  ↓
Validation layer — check required fields present (name, at least 1 experience OR education entry)
  ↓
extraction_confidence score assigned (see below)
  ↓
Store: structured fields → PostgreSQL, raw_extracted_json → PostgreSQL JSONB, embedding → Qdrant
```

### Candidate Canonical Profile (LLM output contract)
Every candidate must be converted into this shape before storage:

```json
{
  "identity": {
    "linkedin_url": "linkedin.com/in/priyanshu-bansal",
    "full_name": "Priyanshu Bansal",
    "headline": "Software Engineer @ WheelsEye",
    "location": "Gurugram, Haryana, India",
    "email": null,
    "phone": null
  },
  "summary": "...",
  "experience": [
    {
      "company": "WheelsEye",
      "role": "Software Engineer",
      "start_date": "2026-06",
      "end_date": null,
      "description": "..."
    }
  ],
  "education": [
    {
      "institution": "...",
      "degree": "...",
      "field": "...",
      "start_date": "...",
      "end_date": "..."
    }
  ],
  "skills": {
    "original": ["MERN", "AWS"],
    "normalized": ["React", "Node.js", "MongoDB", "Express.js", "EC2", "S3", "Lambda", "Cloud Computing"]
  },
  "total_experience_months": 6,
  "other_sections": {
    "certifications": [],
    "projects": [],
    "publications": [],
    "languages": [],
    "awards": []
  }
}
```

### Extraction Confidence Scoring
Assign `extraction_confidence` (0–1) based on:
- Was a name found? (required — if not, confidence = 0, flag for manual review, do not silently store)
- Was at least one experience or education entry found?
- Did the LLM output parse as valid JSON on first attempt, or did it require a repair/retry pass?
- Are dates in a plausible format (not hallucinated)?

Candidates with `extraction_confidence < 0.6` should be visually flagged in the recruiter UI ("⚠ Low confidence extraction — please review") rather than silently trusted. This prevents bad parses from quietly polluting search results.

---

## Part 2 — Skill Normalization

Skills must be expanded from shorthand/umbrella terms into their constituent normalized skills, so search can match on individual technologies even if the candidate only wrote the umbrella term.

### Examples

**MERN** →
```
React, Node.js, MongoDB, Express.js
```

**Frontend Engineer** →
```
React, JavaScript, HTML, CSS, Frontend Development
```

**AWS** →
```
EC2, S3, Lambda, Cloud Computing
```

### Implementation Note
Maintain a normalization dictionary (editable config file, not hardcoded in logic) so new mappings can be added without code changes as recruiters encounter new shorthand terms. Store both `original_skill` and `normalized_skills` (see `03_DatabaseDesign.md`) — never discard the original, since recruiters may want to see exactly what the candidate wrote.

---

## Part 3 — JD Parsing

Convert recruiter's free-text Job Description into structured filters before matching runs.

### Output Contract
```json
{
  "role": "Senior Frontend Engineer",
  "required_skills": ["React", "TypeScript"],
  "preferred_skills": ["AWS", "GraphQL"],
  "experience": { "min_years": 5, "max_years": null },
  "location": "Bangalore",
  "industry": null
}
```

This same local LLM (Qwen2.5) handles this — one extra prompt call per search, negligible latency impact.

---

## Part 4 — Matching Algorithm

### Stage 1 — Metadata Filtering (Qdrant payload filter)
Hard filters applied before any semantic search runs, using the parsed JD:
- `total_experience_months >= min_years * 12` (if specified)
- `location` match (if specified — should be fuzzy/contains, not exact string match, since "Bangalore" should match "Bengaluru, India")
- `candidate_status != 'rejected'` (unless recruiter explicitly includes rejected candidates in search scope)

### Stage 2 — Vector Search
Run dense vector similarity search (BGE-small embeddings) against the canonical profile text of all candidates passing Stage 1. Retrieve top 50–100 candidates.

**Recommended addition — Hybrid retrieval:** Run BM25 keyword search in parallel with the vector search (catches exact skill names, company names, and acronyms that embeddings sometimes blur), then merge both result sets using Reciprocal Rank Fusion (RRF, k=60) before reranking. This is the standard production pattern and meaningfully improves recall over vector-only search, especially for exact terms like "AWS" or specific company names.

### Stage 3 — Reranking
Take the merged top 100 candidates → BGE-reranker-v2-m3 cross-encoder scores each candidate against the full JD text → return top 20.

### Final Score Composition
| Component | Weight |
|---|---|
| Semantic match (reranker score) | 50% |
| Skill match (overlap between JD required/preferred skills and candidate normalized_skills) | 25% |
| Role match (JD role vs candidate current_role / headline similarity) | 15% |
| Experience match (how close candidate's total_experience_months is to JD's required range) | 10% |

### Match Explanation (Required — not optional)
For every returned candidate, the system must show WHY they matched, not just a score. Generate from:
- Which required/preferred skills overlapped (explicit list)
- The specific experience entry that most closely matches the JD's role (e.g. "3 years as Software Engineer at WheelsEye")
- The reranker's top-contributing text span if extractable, or a short LLM-generated one-line explanation if not

This is the feature that makes recruiters trust the ranking instead of treating it as a black box — do not skip it to save build time.

---

## Part 5 — Re-upload Handling (Identity Resolution)

### Priority Order for Matching an Uploaded PDF to an Existing Candidate
```
1. LinkedIn URL (exact match) — most reliable identifier
2. Email (exact match)
3. Phone (exact match)
4. Name + Current Company (fuzzy match — both must match closely)
```

### Behavior on Match Found
```
Default: UPDATE existing profile (not create duplicate)
  ↓
1. Create a candidate_versions record (previous_profile_json, updated_profile_json, changes_summary)
2. Recompute embeddings for the updated canonical profile
3. Recompute extraction_confidence
4. Preserve: candidate_status, notes, candidate_id (never regenerate the UUID)
5. Increment current_version
```

If recruiter explicitly wants a duplicate (rare, e.g. testing), provide an override option in the upload UI — but default behavior must always be "update."

### Changes Summary Generation
Diff the previous and updated canonical profile JSON, output human-readable bullet points:
```
+ Added Software Engineer role
+ Added AWS skill
+ Updated location
~ Changed headline from "Intern" to "Software Engineer"
```
Shown in the candidate's profile view under "Version History" — this is a strong client-facing feature, do not deprioritize it.

---

## Part 6 — Natural Language Search

Recruiters may type queries like:
```
"React developers in Bangalore with AWS and 5+ years"
```

This must be parsed the same way as a JD (Part 3) — extract role/skills/location/experience — then run through the same Stage 1–3 matching pipeline. There is no separate "natural language search" system; it reuses JD parsing + matching entirely. Keep these as one code path, not two.
