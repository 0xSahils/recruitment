# Product Requirements Document (PRD)

## Product Name
AI Recruitment Intelligence Platform

## Objective
Build an AI-powered recruitment platform that allows recruiters to:
- Upload LinkedIn PDF profiles in bulk
- Automatically extract and structure candidate data
- Store candidates in a searchable database
- Match candidates against Job Descriptions using semantic + keyword search
- Filter candidates using recruiter-defined criteria
- Update candidate information manually
- Handle candidate re-uploads intelligently (update, not duplicate)
- Scale from 100 to 10,000+ candidates without architecture changes

## Hard Constraint — Data Privacy
No candidate data may be sent to any third-party AI service (no OpenAI API, no cloud LLM, no managed RAG service) in production. All parsing, embedding, and inference must run on infrastructure the client controls. This constraint shapes every architectural decision in this document set — see `02_Architecture.md` Section "Privacy Boundary."

## Primary User
Recruiter (non-technical, used to ATS/Excel-style tools, not a developer)

## Secondary User (Phase 2, not in beta scope)
Hiring Manager — read-only access to shortlisted candidates

---

## User Flow

```
Login
  ↓
Upload LinkedIn PDFs (bulk, drag-drop)
  ↓
System Extracts Data (async, background job)
  ↓
Candidate Database Updated (new candidates created OR existing candidates updated via identity match)
  ↓
Recruiter Enters JD (free text)
  ↓
AI Matches Candidates (metadata filter → vector search → rerank)
  ↓
Recruiter Filters Results (location, experience, status)
  ↓
Recruiter Reviews Profile (full extracted data + match explanation)
  ↓
Recruiter Edits / Adds Notes / Updates Status
  ↓
Recruiter Contacts Candidate (external — email/phone, status updated manually)
```

---

## Success Metrics

| Area | Target |
|---|---|
| Parsing accuracy | 95%+ field-level extraction accuracy on standard LinkedIn PDF export |
| Search relevance | Top 10 results judged recruiter-relevant in manual review |
| Upload performance | 100 PDFs processed (parsed + embedded + stored) in under 5 minutes |
| Scale | System remains responsive at 10,000+ candidates with no query degradation |
| Re-upload correctness | 0% unintended duplicate candidates created across repeated uploads |

---

## In Scope (Beta / Demo — 100 candidates)
- Bulk PDF upload (drag-drop, up to 100 files at once)
- Full structured extraction (see `03_DatabaseDesign.md`)
- JD-based semantic search with ranked results + match explanation
- Manual candidate editing (every field)
- Candidate status pipeline (New → Contacted → Interview Scheduled → Rejected → Hired)
- Recruiter notes per candidate
- Re-upload detection via LinkedIn URL / email / phone / name+company
- Version history per candidate (what changed, when)
- Natural language search ("React developers in Bangalore with AWS and 5+ years")
- CSV export of filtered/shortlisted candidates
- Single-tenant, single-recruiter-role login (no complex RBAC yet)

## Explicitly Out of Scope (Beta)
- Multi-recruiter roles / permissions
- Email/calendar integration for outreach
- Resume formats other than LinkedIn PDF export (generic resume parsing is a future phase)
- Mobile app (web responsive only)
- Candidate-facing portal

## Out of Scope but Architecturally Reserved For (Production, post-approval)
- 10,000+ candidate scale (architecture must support this from day 1, even if beta only loads 100)
- Multi-tenant support if platform is resold to other recruitment agencies
- Audit logging for compliance

---

## Constraints Summary
| Constraint | Implication |
|---|---|
| No 3rd-party AI services in production | Self-hosted LLM (Ollama), self-hosted embeddings, self-hosted reranker |
| Beta runs on developer's laptop (16GB RAM, no GPU) | Must select CPU-friendly small models for beta; full power reserved for production VM |
| Production budget ~₹10,000–15,000/month | Azure VM sizing must stay within this — see `02_Architecture.md` |
| 3–5 day build window for demo | Document set exists specifically to prevent architectural rework mid-build |
