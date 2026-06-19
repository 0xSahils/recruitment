# Development Plan

## Build Window: 4–5 Days (Beta/Demo, 100 candidates, local laptop)

---

## Day 0 — Environment Setup (do this before giving docs to AI agent)
- [ ] Install PostgreSQL locally (or Docker container)
- [ ] Install Qdrant locally (Docker container — `docker run -p 6333:6333 qdrant/qdrant`)
- [ ] Install Ollama natively (not Docker — better CPU performance)
- [ ] Pull models: `ollama pull qwen2.5:3b` (start small given laptop specs — see `02_Architecture.md`), `ollama pull bge-small` or equivalent embedding model via sentence-transformers
- [ ] Verify all three services running and reachable before writing any application code
- [ ] Free up laptop disk space (target 30GB+ free) — model weights + Docker images add up

## Day 1 — Backend Foundation
- [ ] FastAPI project scaffold
- [ ] PostgreSQL schema migration from `03_DatabaseDesign.md` (use Alembic)
- [ ] Qdrant collection setup with metadata payload schema
- [ ] PDF upload endpoint (`POST /candidates/upload`) — file handling only, no parsing logic yet
- [ ] PyMuPDF text extraction — verify raw text quality on 3–5 real LinkedIn PDFs before building the LLM parsing layer on top

## Day 2 — Parsing & Identity Resolution
- [ ] LLM parsing prompt (Qwen2.5) — implement Candidate Canonical Profile extraction from `04_AIMatchingSpec.md` Part 1
- [ ] Extraction confidence scoring logic
- [ ] Skill normalization dictionary + expansion logic (Part 2)
- [ ] Identity resolution logic (Part 5) — LinkedIn URL → email → phone → name+company priority chain
- [ ] Version tracking + changes_summary diff generation
- [ ] Test: upload same candidate's PDF twice with a small change, verify update-not-duplicate behavior works correctly

## Day 3 — Matching Pipeline & Search API
- [ ] JD parsing prompt (Part 3)
- [ ] Stage 1 metadata filtering (Qdrant payload filter)
- [ ] Stage 2 hybrid retrieval — vector search + BM25, merged via RRF
- [ ] Stage 3 reranking (BGE-reranker-v2-m3)
- [ ] Final score composition (weighted: semantic 50%, skill 25%, role 15%, experience 10%)
- [ ] Match explanation generation
- [ ] `POST /search` endpoint wired end to end
- [ ] Test with 5–10 sample JDs against the uploaded candidate pool — sanity check results manually before moving to frontend

## Day 4 — Frontend
- [ ] Next.js + shadcn/ui scaffold
- [ ] Login page (hardcoded auth)
- [ ] Dashboard page (search bar + ranked candidate cards) — see `06_UIWireframes.md` Page 2
- [ ] Upload page with progress polling — Page 3
- [ ] Candidate Profile page (view + inline edit) — Page 4
- [ ] Candidates list/table page — Page 5
- [ ] Wire all pages to API contracts in `05_APIContracts.md`

## Day 5 — Demo Prep & Polish
- [ ] Load all 100 real demo PDFs, verify processing completes under 5 minutes (PRD success metric)
- [ ] Run 5 demo JD searches, confirm top 10 results look relevant
- [ ] Fix any low extraction_confidence cases found during real testing
- [ ] Full offline test — disconnect WiFi, confirm everything still works (proves the privacy/local claim live)
- [ ] CSV export sanity check
- [ ] Rehearse demo script 2–3 times

---

## Demo Script (for client presentation)

**Act 1 — Upload (2 min):** Drag 10–15 real LinkedIn PDFs in, show live progress, point out one "Updated (v2)" result if a re-upload is included in the demo set.

**Act 2 — Search (3 min):** Paste a real JD, walk through the ranked results, explicitly point at the match explanations: *"It's not just a score — it tells you exactly why."*

**Act 3 — Edit (1 min):** Open a candidate, change status to Shortlisted, add a note, show it auto-saves.

**Act 4 — Export (30 sec):** Filter to Shortlisted, export CSV, open it.

**Act 5 — Privacy (1 min):** *"Everything you just saw ran locally — no candidate data was sent to OpenAI or any external AI company. In production this runs entirely inside your own cloud account."*

---

## Production Deployment (Post-Approval)

### Infrastructure
- Azure VM: Standard D4s v3 (4 vCPU, 16GB RAM), Central India region
- Upgrade models: Qwen2.5:7b or 14b (better parsing/matching quality with real server hardware)
- Move Qdrant + PostgreSQL to the same VM or separate managed instances depending on budget
- Add Celery + Redis for background job queue (replaces FastAPI BackgroundTasks at scale)

### Cost Estimate (Monthly)
| Item | Cost (INR) |
|---|---|
| Azure D4s v3 VM (1-year reserved) | ~₹8,100 |
| 128GB SSD managed disk | ~₹835 |
| Bandwidth | ~₹415 |
| **Total infra cost** | **~₹9,350–10,600** |
| **Quote to client** | **₹15,000/month** (covers maintenance margin) |

### Production Checklist (not in beta scope, flag for later)
- [ ] Proper multi-user authentication
- [ ] Soft-delete + audit logging
- [ ] Backup strategy for PostgreSQL + Qdrant
- [ ] Move background jobs to Celery + Redis queue
- [ ] Load test at 10,000+ candidates
- [ ] Monitoring/alerting on the VM

---

## Document Index
```
/Docs
  01_PRD.md                — what we're building, for whom, success metrics
  02_Architecture.md        — tech stack, privacy boundary, deployment
  03_DatabaseDesign.md      — full schema, all entities
  04_AIMatchingSpec.md      — parsing pipeline, matching algorithm, identity resolution
  05_APIContracts.md        — every endpoint, request/response shapes
  06_UIWireframes.md        — every page, layout, behavior notes
  07_DevelopmentPlan.md     — this file — day-by-day build sequence
```

## Instruction for AI Coding Agent (Cursor/Claude Code)
> Read all 7 documents in `/Docs` completely before writing any code. Build in the order specified in this Development Plan — do not skip ahead to frontend before the matching pipeline is tested and working. Every architectural decision (tech choices, schema, API shapes) is already made in these documents — do not introduce new tools, services, or third-party AI APIs not listed in `02_Architecture.md`. If a requirement is ambiguous, ask rather than assume — particularly around the privacy boundary, which is a hard constraint, not a preference.
