# Execution Playbook — AI Recruitment Platform

_Complete project planning with dependencies, milestones, and build-all-at-once strategy_

---

## PROJECT OVERVIEW

**Name:** AI Recruitment Intelligence Platform  
**Goal:** Beta MVP for 1 recruiter, 100 candidates, full JD-based semantic matching  
**Timeline:** 4–5 days (1 developer)  
**Environment:** Local development (16GB RAM, no GPU), then production on Azure D4s v3  
**Hard Constraint:** Zero 3rd-party AI APIs with real candidate data (privacy boundary = everything runs locally)

---

## PHASE 1: PRE-BUILD VALIDATION (Before Day 1)

### Checklist

- [ ] PostgreSQL running locally (or via Docker)
- [ ] Qdrant running locally (Docker: `docker run -p 6333:6333 qdrant/qdrant`)
- [ ] Ollama installed natively, pulling models:
  - [ ] `ollama pull qwen2.5:3b` (parsing LLM — if laptop struggles, this is main candidate for upgrade)
  - [ ] `ollama pull mistral:7b` (fallback if qwen2.5 isn't available)
  - [ ] BGE embedding model available (via sentence-transformers library)
  - [ ] BGE reranker model available (via FlagEmbedding library)
- [ ] All services reachable and test-pinged (curl to localhost:6333 for Qdrant, curl to localhost:11434 for Ollama health)
- [ ] 30GB+ free disk space confirmed
- [ ] 5 real LinkedIn PDFs on hand for initial parsing QA tests
- [ ] Python 3.10+ environment ready (venv or conda)

**Exit Criteria:** All services running, no connectivity errors, models downloaded and verified.

---

## PHASE 2: ARCHITECTURE DEEP DIVE

### System Topology (Confirmed)

```
┌──────────────────────┐
│  React Frontend      │ Next.js + shadcn/ui + Tailwind
│  (Dashboard/Upload)  │
└──────────┬───────────┘
           │ REST (JSON)
┌──────────▼──────────┐
│  FastAPI Backend    │ Python, async
│                      │
├─ Upload handler     │
├─ Search pipeline    │
├─ Candidate CRUD     │
└──────────┬──────────┘
      ┌────┴────┬────────┬──────────┐
      │         │        │          │
┌─────▼──┐ ┌────▼──┐ ┌──▼──────┐ ┌─▼──────────┐
│ PgSQL  │ │Qdrant │ │ Ollama  │ │ File Store │
│ (rel)  │ │(vecs) │ │(LLM)    │ │ (PDFs)     │
└────────┘ └───────┘ └─────────┘ └────────────┘
```

### Key Architectural Decisions

| Decision                         | Rationale                                                             | Locked? |
| -------------------------------- | --------------------------------------------------------------------- | ------- |
| FastAPI for backend              | Python ecosystem (PDF + LLM libraries) + async                        | ✓ Yes   |
| PostgreSQL primary DB            | Structured candidate data, scales to 10k+, JSONB for raw extracts     | ✓ Yes   |
| Qdrant for vectors               | Local deployment, metadata filtering in queries, production-ready     | ✓ Yes   |
| Qwen2.5 for parsing              | Instruction-following, CPU-friendly, fully local, Apache 2.0 licensed | ✓ Yes   |
| BGE-small for embeddings         | ~130MB, strong quality/size ratio, CPU-friendly                       | ✓ Yes   |
| BGE-reranker-v2-m3 for reranking | Best quality/latency balance, ~145ms on CPU                           | ✓ Yes   |
| Next.js + shadcn/ui for frontend | Fast iteration, professional components, TypeScript                   | ✓ Yes   |
| TanStack Query + Table           | Async state management, sortable/filterable views                     | ✓ Yes   |

**No Deviations Allowed:** Any suggestion to use OpenAI, Anthropic, Gemini, or any cloud LLM API is a constraint violation. Stop and flag it.

---

## PHASE 3: BUILD BREAKDOWN & DEPENDENCY GRAPH

### Module Dependency Chain

```
Core Database Models
      ↓
API Contracts (Request/Response schemas)
      ↓
┌─ PDF Parsing Module ──────┐
│ PyMuPDF text extraction   │
│ Qwen2.5 LLM parsing       │
│ Extraction confidence     │
└──────────┬────────────────┘
           ↓
      Identity Resolution
      ↓
      Skill Normalization
      ↓
      Vector Embeddings (BGE-small)
      ↓
┌─ Search Module ───────────────────┐
│ JD parsing (Qwen2.5)              │
│ Stage 1: Metadata filtering       │
│ Stage 2: Hybrid retrieval (RRF)   │
│ Stage 3: Reranking (BGE-reranker) │
│ Match explanation generation      │
└──────────┬──────────────────────────┘
           ↓
Upload Queue & Async Job Processing
      ↓
API Endpoints (FastAPI routes)
      ↓
Frontend Components & Pages
```

### Per-Module Checklist

#### **MODULE 1: Database & ORM Layer**

```
Deliverables:
  ✓ PostgreSQL schema (Alembic migrations)
  ✓ SQLAlchemy ORM models
  ✓ Connection pooling setup
  ✓ Indexes on identity fields (linkedin_url, email, phone, name+company combo)

Inputs:
  - 03_DatabaseDesign.md (entity specs)

Outputs:
  - alembic/versions/001_init_schema.py
  - app/models/*.py (Candidate, Experience, Education, Skills, etc.)
  - app/db.py (session factory, connection pool)

Time Estimate: 3–4 hours
Dependencies: None (can start immediately)
Test: `pytest test/test_models.py` — verify schema creates, no FK constraint errors
```

#### **MODULE 2: Vector DB Setup**

```
Deliverables:
  ✓ Qdrant client initialization
  ✓ Collection schema with metadata payload
  ✓ Utility functions for embedding/upsert/search

Inputs:
  - 04_AIMatchingSpec.md (Stage 1–3 requirements)

Outputs:
  - app/vector_db.py (Qdrant client + collection manager)
  - Vector schema: { id, embedding, candidate_id, skills, experience_years, location }

Time Estimate: 2–3 hours
Dependencies: None (parallel with Module 1)
Test: Create dummy embedding, upsert, search, verify retrieval
```

#### **MODULE 3: Ollama Integration & LLM Prompts**

```
Deliverables:
  ✓ Ollama HTTP client wrapper
  ✓ Parsing prompt (Candidate Canonical Profile extraction)
  ✓ JD parsing prompt (query intent extraction)
  ✓ Skill normalization prompt
  ✓ Match explanation prompt

Inputs:
  - 04_AIMatchingSpec.md Parts 1, 2, 3, 4

Outputs:
  - app/llm/prompts.py (all prompt templates)
  - app/llm/client.py (Ollama HTTP interface)
  - app/llm/parsers.py (JSON output validation, retry logic)

Time Estimate: 4–5 hours (includes iterative testing on 3–5 real PDFs)
Dependencies: Modules 1, 2
Test: Run parsing on 5 sample PDFs, manually verify JSON output quality, check confidence scoring
```

#### **MODULE 4: PDF Extraction & Text Preprocessing**

```
Deliverables:
  ✓ PyMuPDF setup for LinkedIn PDF text extraction
  ✓ Layout-aware text chunking (preserve section structure)
  ✓ Cleanup pipeline (handle OCR errors, malformed text)

Inputs:
  - 5 real LinkedIn PDF samples

Outputs:
  - app/pdf/extractor.py (PyMuPDF wrapper)
  - app/pdf/preprocessor.py (text cleaning + chunking)

Time Estimate: 2–3 hours
Dependencies: None
Test: Extract text from 5 PDFs, visually compare with original to ensure quality
```

#### **MODULE 5: Identity Resolution & Deduplication**

```
Deliverables:
  ✓ LinkedIn URL matching (exact + normalized)
  ✓ Email matching
  ✓ Phone matching
  ✓ Name + company fuzzy matching
  ✓ Priority chain logic (see 04_AIMatchingSpec.md Part 5)
  ✓ Version tracking + diff generation

Inputs:
  - 04_AIMatchingSpec.md Part 5
  - 03_DatabaseDesign.md (candidate_versions table)

Outputs:
  - app/identity/resolver.py (matching logic)
  - app/identity/differ.py (changes summary generation)

Time Estimate: 3–4 hours
Dependencies: Module 1 (database models)
Test: Upload same candidate twice with small change, verify: (a) no duplicate candidate created, (b) version 2 created with changes_summary populated
```

#### **MODULE 6: Skill Normalization**

```
Deliverables:
  ✓ Skill dictionary (original → normalized mapping)
  ✓ Expansion logic (e.g., "MERN" → ["React", "Node.js", "MongoDB", "Express"])
  ✓ LLM-based skill extraction from job descriptions/experience

Inputs:
  - 04_AIMatchingSpec.md Part 2

Outputs:
  - app/skills/dictionary.py (skill ontology)
  - app/skills/normalizer.py (expansion + deduplication)

Time Estimate: 2–3 hours
Dependencies: Module 3 (LLM client)
Test: Normalize 20+ skill variations, verify expansions are semantically correct
```

#### **MODULE 7: Parsing Pipeline (Orchestration)**

```
Deliverables:
  ✓ End-to-end parse: PDF → PyMuPDF → LLM → Validation → DB insert → Qdrant upsert

Inputs:
  - Modules 1–6

Outputs:
  - app/parsing/pipeline.py (orchestrator)
  - app/parsing/validators.py (extraction quality checks, confidence scoring)

Time Estimate: 4–5 hours
Dependencies: All modules 1–6
Test: Upload 10 PDFs, verify all stored in PostgreSQL + Qdrant, confidence scores assigned, extraction_confidence < 0.6 for any bad parses
```

#### **MODULE 8: Embedding Generation**

```
Deliverables:
  ✓ BGE-small embedding model loading
  ✓ Candidate text composition (concatenate name, headline, summary, skills, experience descriptions)
  ✓ Batch embedding for efficiency

Inputs:
  - 04_AIMatchingSpec.md Stage 2

Outputs:
  - app/embeddings/generator.py (text composition + batch embedding)
  - app/embeddings/cache.py (optional: cache embeddings on disk for large batches)

Time Estimate: 2–3 hours
Dependencies: Module 3 (LLM client for text prep)
Test: Generate embeddings for 20 candidates, verify no NaN, shape correct (384-dim for BGE-small)
```

#### **MODULE 9: Search & Matching Pipeline (JD Parsing → Retrieval → Ranking)**

```
Deliverables:
  ✓ Stage 1: JD parsing → query intent (required skills, experience range, location, role)
  ✓ Stage 2: Metadata filtering on Qdrant
  ✓ Stage 2B: Vector search + BM25 hybrid (RRF merging)
  ✓ Stage 3: Reranking with BGE-reranker-v2-m3
  ✓ Final scoring: weighted composition
  ✓ Match explanation generation (see 04_AIMatchingSpec.md Part 4)

Inputs:
  - 04_AIMatchingSpec.md Parts 3, 4
  - Modules 1–8

Outputs:
  - app/search/jd_parser.py (query intent extraction)
  - app/search/retrieval.py (Qdrant filtering + vector search + BM25)
  - app/search/reranker.py (BGE reranker orchestration)
  - app/search/scorer.py (final score composition)
  - app/search/explainer.py (match explanation generation)

Time Estimate: 6–8 hours (most complex module)
Dependencies: All modules 1–8
Test: Run 5 demo JDs against 50+ candidate pool, manually validate top 10 results for relevance, check explanations are sensible
```

#### **MODULE 10: Upload API Endpoint & Queue**

```
Deliverables:
  ✓ POST /api/v1/candidates/upload (multipart file handling)
  ✓ Batch ID generation
  ✓ FastAPI BackgroundTasks for async parsing
  ✓ GET /api/v1/candidates/upload/{batch_id}/status (progress polling)

Inputs:
  - 05_APIContracts.md (Upload section)
  - Module 7 (Parsing pipeline)

Outputs:
  - app/api/routes/upload.py (endpoint handlers)
  - app/queue/manager.py (batch tracking, progress persistence)

Time Estimate: 3–4 hours
Dependencies: Modules 1, 7
Test: Upload 20 PDFs, poll status endpoint every 2s, verify progress, final counts match
```

#### **MODULE 11: CRUD API Endpoints**

```
Deliverables:
  ✓ GET /api/v1/candidates (list/filter, paginated)
  ✓ GET /api/v1/candidates/{id} (full profile)
  ✓ PATCH /api/v1/candidates/{id} (edit candidate)
  ✓ POST /api/v1/search (search endpoint, calls Module 9)
  ✓ POST /api/v1/export (CSV export of candidates)

Inputs:
  - 05_APIContracts.md
  - Modules 1, 9

Outputs:
  - app/api/routes/candidates.py
  - app/api/routes/search.py
  - app/api/routes/export.py

Time Estimate: 4–5 hours
Dependencies: Modules 1, 9
Test: CRUD each endpoint, verify response shapes match contracts, test pagination, filtering, CSV export
```

#### **MODULE 12: Authentication (Hardcoded Beta)**

```
Deliverables:
  ✓ Single recruiter login (username: demo, password: demo123)
  ✓ Session cookie creation + validation
  ✓ Logout endpoint

Inputs:
  - 06_UIWireframes.md (Login page)

Outputs:
  - app/api/routes/auth.py
  - app/auth/session.py (cookie + session logic)

Time Estimate: 1–2 hours
Dependencies: Module 1 (if storing user in DB, which we won't for beta)
Test: Login, get session cookie, make authenticated request, verify auth enforced
```

#### **MODULE 13: Frontend Infrastructure**

```
Deliverables:
  ✓ Next.js + TypeScript scaffold
  ✓ shadcn/ui component library installation
  ✓ Tailwind CSS config
  ✓ TanStack Query setup
  ✓ TanStack Table setup
  ✓ API client (fetch wrapper with auth headers)

Inputs:
  - 06_UIWireframes.md

Outputs:
  - next.config.js
  - tailwind.config.js
  - lib/api-client.ts
  - hooks/useQuery, useMutation
  - pages/ structure

Time Estimate: 2–3 hours
Dependencies: None
Test: `npm run dev`, verify frontend runs on localhost:3000, no build errors
```

#### **MODULE 14: Frontend Pages (4 pages)**

```
Deliverables:
  ✓ Page 1: Login (email + password form)
  ✓ Page 2: Dashboard (search bar + ranked candidate cards)
  ✓ Page 3: Upload (drag-drop + progress queue)
  ✓ Page 4: Candidate Profile (view + inline edit, notes, status)
  ✓ Page 5: Candidates Table (sortable, filterable, paginated)

Inputs:
  - 06_UIWireframes.md (full designs)
  - 05_APIContracts.md (response shapes)
  - Module 11 (API endpoints)

Outputs:
  - pages/login.tsx
  - pages/dashboard.tsx
  - pages/upload.tsx
  - pages/candidates/[id].tsx
  - pages/candidates.tsx
  - components/CandidateCard.tsx
  - components/UploadQueue.tsx
  - etc.

Time Estimate: 12–15 hours
Dependencies: Modules 11, 12, 13
Test: Visit each page, test interactions (search, upload, edit, filter), verify API calls are made correctly
```

#### **MODULE 15: Glue & Integration Testing**

```
Deliverables:
  ✓ End-to-end test: Upload → Parse → Search → Edit
  ✓ E2E test with 100 real PDFs
  ✓ Performance baseline (5-min target for 100 PDFs)
  ✓ Extraction confidence QA review
  ✓ Bug fixes from initial full run

Inputs:
  - All modules 1–14
  - 100 real LinkedIn PDFs

Outputs:
  - test/e2e_test.py (backend)
  - test/e2e.spec.ts (frontend, Playwright optional)
  - Demo results + timings

Time Estimate: 4–6 hours
Dependencies: Modules 1–14 (all complete)
Test: Run full demo workflow with real data, measure timings, document any issues
```

---

## PHASE 4: DETAILED BUILD SCHEDULE

### **Day 0 (Evening before Day 1) — Environment Validation**

**Duration:** 2–3 hours

1. Install/verify PostgreSQL, Qdrant, Ollama running
2. Test model downloads (qwen2.5:3b, BGE models)
3. Free disk space to 30GB+
4. Verify all services reachable via localhost
5. Prepare 5 sample PDFs for parsing QA

**Exit:** All services confirmed running, models available, disk space OK.

---

### **Day 1 — Backend Foundation (Modules 1–4)**

**Duration:** 8 hours

| Time        | Module | Task                                                |
| ----------- | ------ | --------------------------------------------------- |
| 00:00–02:00 | 1      | PostgreSQL schema + Alembic setup                   |
| 02:00–03:30 | 1      | SQLAlchemy ORM models + indexes                     |
| 03:30–05:00 | 2      | Qdrant client + collection setup                    |
| 05:00–07:00 | 3      | Ollama wrapper + initial prompts draft              |
| 07:00–08:00 | 4      | PyMuPDF integration, text extraction test on 5 PDFs |

**Checkpoint:** Database tables created, Qdrant collection exists, PyMuPDF extraction working, Ollama connectivity verified.

---

### **Day 2 — Parsing, Identity, Skills (Modules 5–8)**

**Duration:** 8 hours

| Time        | Module | Task                                                                 |
| ----------- | ------ | -------------------------------------------------------------------- |
| 00:00–01:30 | 3      | Refine parsing prompt (iterate on 5 PDFs, check JSON output quality) |
| 01:30–02:30 | 3      | Extraction confidence scoring logic                                  |
| 02:30–04:00 | 5      | Identity resolution (LinkedIn URL → email → phone → name+company)    |
| 04:00–05:30 | 5      | Version tracking + diff generation                                   |
| 05:30–07:00 | 6      | Skill normalization dictionary + expansion                           |
| 07:00–08:00 | 7      | Integrate Modules 5–6 into full parsing pipeline                     |

**Checkpoint:** Parse 10 PDFs end-to-end, store in PostgreSQL + Qdrant, verify duplicate detection logic works (upload same PDF twice → expect version 2, no new duplicate).

---

### **Day 3 — Search & Matching (Modules 9–10)**

**Duration:** 8 hours

| Time        | Module | Task                                            |
| ----------- | ------ | ----------------------------------------------- |
| 00:00–01:00 | 9      | JD parsing prompt (extract intent) + test       |
| 01:00–02:30 | 9      | Metadata filtering on Qdrant (Stage 1)          |
| 02:30–04:00 | 9      | Vector search + BM25 hybrid retrieval (Stage 2) |
| 04:00–05:00 | 9      | Reranking with BGE-reranker-v2-m3 (Stage 3)     |
| 05:00–06:00 | 9      | Final scoring + match explanation generation    |
| 06:00–07:30 | 10     | Upload endpoint + async job queue               |
| 07:30–08:00 | 10     | Status polling endpoint                         |

**Checkpoint:** Search 50-candidate pool with 5 test JDs, manually verify top results are relevant, run 20-PDF upload end-to-end.

---

### **Day 4 — API & Frontend (Modules 11–14)**

**Duration:** 10–12 hours

| Time        | Module | Task                                                  |
| ----------- | ------ | ----------------------------------------------------- |
| 00:00–02:00 | 11     | GET/PATCH candidates endpoints + CSV export           |
| 02:00–03:00 | 12     | Auth endpoints (hardcoded login)                      |
| 03:00–05:00 | 13     | Next.js scaffold + shadcn/ui + TanStack setup         |
| 05:00–08:00 | 14     | Login page + Dashboard (search bar + candidate cards) |
| 08:00–10:00 | 14     | Upload page + progress queue visualization            |
| 10:00–12:00 | 14     | Candidate profile page + candidates table page        |

**Checkpoint:** Frontend runs, all pages accessible, login works, API calls functional.

---

### **Day 5 — Integration, Testing, Demo (Modules 15 + Polish)**

**Duration:** 8 hours

| Time        | Task                                                               |
| ----------- | ------------------------------------------------------------------ |
| 00:00–02:00 | Load all 100 real PDFs, begin upload                               |
| 02:00–04:00 | Monitor parsing (target: complete in <5 min)                       |
| 04:00–05:00 | Run 5–10 demo JDs, manually validate results                       |
| 05:00–06:00 | QA low-confidence candidates, fix any parsing issues               |
| 06:00–07:00 | Full offline test (disconnect WiFi, verify everything still works) |
| 07:00–08:00 | Rehearse demo script 2–3 times, document timings                   |

**Checkpoint:** 100 candidates uploaded & searchable, top results manually validated, demo ready.

---

## PHASE 5: MILESTONE GATES & SUCCESS CRITERIA

### Milestone 1: Day 1 End

**Success = "Can I parse and store a candidate?"**

- [ ] PostgreSQL schema created (Alembic migration runs cleanly)
- [ ] Qdrant collection exists and accepts vectors
- [ ] PyMuPDF extracts text from 5 real PDFs without errors
- [ ] Ollama endpoint responds to requests

### Milestone 2: Day 2 End

**Success = "Can I upload, parse, deduplicate, and re-upload?"**

- [ ] 10 PDFs uploaded, parsed, stored in PostgreSQL (candidates table populated)
- [ ] Each candidate has an embedding in Qdrant
- [ ] Uploading the same PDF twice produces: (a) no duplicate candidate, (b) version 2 in candidate_versions with changes_summary
- [ ] Extraction confidence scoring works (manually verify 0.6–0.9 range for good parses, <0.6 for bad ones)

### Milestone 3: Day 3 End

**Success = "Can I search and get relevant ranked results?"**

- [ ] 50-candidate pool, 5 test JDs searched, top 10 results look recruiter-relevant (manual validation)
- [ ] Match explanations generated and sensible (e.g., "Has React and AWS skills", "5+ years experience")
- [ ] 20-PDF upload completes without errors
- [ ] Status polling endpoint shows progress in real time

### Milestone 4: Day 4 End

**Success = "Does the frontend UI work end-to-end?"**

- [ ] Login page: enter (demo / demo123) → redirects to dashboard
- [ ] Dashboard: paste JD → see ranked candidate cards with match scores + explanations
- [ ] Upload page: drag-drop 10 PDFs → see live progress queue → see results (new / updated / failed counts)
- [ ] Candidate profile: click a card → view full profile → edit status/notes → auto-save
- [ ] Candidates table: filter by status, export CSV

### Milestone 5: Day 5 End

**Success = "Is the 100-candidate demo fast and reliable?"**

- [ ] 100 PDFs upload + parse in <5 minutes (PRD metric)
- [ ] 10 demo JD searches run, top results manually validated
- [ ] Offline test: disconnect WiFi, confirm all pages and search still work (privacy claim proven)
- [ ] Demo script rehearsed 2–3 times without errors

---

## PHASE 6: BUILD-ALL-AT-ONCE COORDINATION

### Why "Build All At Once"?

Each module depends on prior modules. **Parallel work is possible but limited.**

**Parallelizable tracks (Day 1):**

- Modules 1 & 2 (database + vector DB) can start simultaneously → results used by everyone else
- Module 3 (LLM prompts) can draft while 1 & 2 develop → refined on Day 2

**Sequential dependencies (Days 2–4):**

- Modules 5–9 (all parsing, identity, search) must be done in order because each layer uses the prior
- Module 14 (frontend) **cannot start** until Module 11 (API) is complete

### Developer Workflow

1. **Days 1–3:** Build backend modules in strict order (1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10)
   - Each module is tested in isolation + against the prior module's output
   - No frontend work until Day 4

2. **Day 4:** While backend is stabilizing with real PDF tests from Day 2–3, frontend (Modules 13–14) runs in parallel
   - Frontend calls stubs/mock endpoints initially, then swaps to real API once stable

3. **Day 5:** Full integration test with real data, demo rehearsal

### Git Commit Strategy

```
Day 1:   commit "backend: db schema + qdrant + pymupdf"
Day 2:   commit "backend: parsing pipeline + identity resolution + skills"
Day 3:   commit "backend: search matching + upload queue"
Day 4:   commit "frontend: next.js scaffold + pages + api integration"
Day 5:   commit "demo: 100-candidate load test + final polish"
```

---

## PHASE 7: CRITICAL DECISION POINTS & GOTCHAS

### Decision Point 1: Parsing Quality (Day 2)

**If** extraction_confidence is low (<0.6) on >20% of real PDFs:

- [ ] **Option A (Recommended):** Refine Qwen2.5 prompt further (add more structure hints, examples)
- [ ] **Option B:** Upgrade model (Qwen2.5:7b if laptop allows, or Mistral:7b)
- [ ] **Option C (Blocked):** Use OpenAI/Gemini API — violates privacy constraint ✗

**Decision Deadline:** End of Day 2 (must finish before matching testing on Day 3)

### Decision Point 2: Search Quality (Day 3)

**If** search results look irrelevant (manual validation of top 10 for 5 JDs):

- [ ] **Option A:** Refine matching weights (currently: semantic 50%, skill 25%, role 15%, exp 10%) — experiment on Day 3
- [ ] **Option B:** Improve embedding quality (e.g., use larger BGE model if GPU available) — **only if CPU version is too slow**
- [ ] **Option C:** Refine reranker prompt or disable reranking, rely on vector search alone
- [ ] **Option D (Blocked):** Use external semantic search API ✗

**Decision Deadline:** Day 3 afternoon (must finish before frontend work)

### Decision Point 3: Performance (Day 5)

**If** 100-PDF upload takes >5 minutes:

- [ ] **Option A:** Parallelize parsing (spawn 4 async tasks instead of 1) — code change in Module 10
- [ ] **Option B:** Pre-compute embeddings in parallel during parsing (instead of sequential) — code change in Module 8
- [ ] **Option C:** Reduce reranking quality (e.g., only rerank top-50 from vector search, not all) — acceptable trade-off for beta

**Decision Deadline:** Day 5 morning (must resolve before demo)

### Gotcha 1: Ollama Model Loading

Ollama models load lazily (first request is slow, ~30 sec).

- **Mitigation:** After Ollama starts, manually run `curl http://localhost:11434/api/generate -d '{"model":"qwen2.5:3b","prompt":"test"}'` to pre-load model before running tests.

### Gotcha 2: Qdrant Vector Dimension Mismatch

BGE-small produces 384-dim embeddings. If the Qdrant collection was created with a different size, upserts will fail.

- **Mitigation:** When setting up Qdrant in Module 2, explicitly set vector_size=384 in collection config.

### Gotcha 3: PyMuPDF PDF Scanning

Some LinkedIn PDFs are scanned images, not text layers. PyMuPDF will return empty strings.

- **Mitigation:** Catch this early in Module 4 preprocessing. Log it as a known failure reason (see API contract error handling), don't crash.

### Gotcha 4: LLM JSON Output Repair

Qwen2.5 sometimes outputs JSON with trailing commas or missing quotes.

- **Mitigation:** In Module 3, add a JSON repair library (e.g., `json-repair` or custom parser) to handle common malformations.

---

## PHASE 8: TESTING STRATEGY

### Unit Tests (Per Module)

- **Module 1:** Test model creation, FK constraints, cascading deletes
- **Module 2:** Test vector upsert, metadata filtering, similarity search
- **Module 3:** Test prompt formatting, LLM response parsing
- **Module 4:** Test text extraction quality on 5 real PDFs
- **Module 5:** Test identity matching (exact, fuzzy, priority chain)
- **Module 6:** Test skill expansion, deduplication
- **Module 7:** Test full parsing pipeline (should reuse Module 1–6 tests)
- **Module 9:** Test JD parsing, stage 1 filtering, stage 2 retrieval, stage 3 reranking
- **Module 11:** Test CRUD endpoints for 400/403/404 errors

### Integration Tests (Cross-Module)

- **E2E 1:** Upload 1 PDF → Parse → Store → Retrieve (Modules 1–7)
- **E2E 2:** Upload 10 PDFs → Search with JD → Get ranked results (Modules 1–11)
- **E2E 3:** Upload same PDF twice → Verify dedup + version tracking (Modules 1, 5, 10)

### Frontend Tests (Modules 13–14)

- **Component:** Verify CandidateCard renders correctly with mock data
- **Page:** Verify login redirects to dashboard on success
- **API Integration:** Mock API calls, test loading/error states
- **E2E (Playwright, optional):** Login → Search → Upload → Edit → Logout

### Performance Tests (Day 5)

- **100 PDFs in 5 min:** Time upload end-to-end, record breakdown (PDF fetch % / parse % / embed % / store %)
- **Search latency:** Time 5 search queries on 100-candidate pool, target <1 sec per query

**Test execution:**

```bash
# Day 1 end: pytest test/test_models.py
# Day 2 end: pytest test/test_parsing.py && pytest test/test_identity.py
# Day 3 end: pytest test/test_search.py && pytest test/test_upload.py
# Day 4 end: pytest test/ && npm run test (frontend)
# Day 5: npm run dev (full manual E2E)
```

---

## PHASE 9: HANDOFF & PRODUCTION CHECKLIST

### Production Deployment (Post-Approval)

This is **not** in beta scope but must be flagged upfront so architecture decisions are compatible.

#### Infrastructure Upgrade

| Component | Beta                    | Production                      |
| --------- | ----------------------- | ------------------------------- |
| VM        | Laptop 16GB             | Azure D4s v3 (4 vCPU, 16GB RAM) |
| Models    | Qwen2.5:3b              | Qwen2.5:7b or 14b               |
| Storage   | Local disk              | Managed SSD (128GB)             |
| Queue     | FastAPI BackgroundTasks | Celery + Redis                  |

#### Cost Estimate (Monthly, India Central region)

| Item                 | Cost (INR)                                        |
| -------------------- | ------------------------------------------------- |
| Azure D4s v3 compute | ₹8,100                                            |
| Managed disk         | ₹835                                              |
| Bandwidth            | ₹415                                              |
| **Total infra**      | **~₹9,350**                                       |
| **Quote to client**  | **₹15,000** (covers maintenance + support margin) |

#### Production Checklist (Post-Beta Approval)

- [ ] Multi-user authentication (AD, OAuth, or custom)
- [ ] Soft-delete + audit logging (candidate edit history)
- [ ] Backup strategy (daily snapshots, point-in-time recovery for PostgreSQL)
- [ ] Move background jobs to Celery + Redis (replace FastAPI BackgroundTasks)
- [ ] Load test at 10,000 candidates + concurrent users
- [ ] Monitoring/alerting (CPU, memory, query latency)
- [ ] HTTPS + TLS cert
- [ ] API rate limiting
- [ ] CORS policy (if frontend on different domain)

---

## PHASE 10: DEMO SCRIPT & MATERIALS

### Act 1 — Upload (2 min)

1. Open frontend, go to Upload page
2. Drag 15 real LinkedIn PDFs into drop zone
3. Watch progress queue — show: "10/15 parsed, 1 updated (v2), 4 processing"
4. Point out: "Updated (v2) means we re-detected an existing candidate and created a new version, no duplicates"
5. Wait for 100% completion, show: ✓ 14 new, ✓ 1 updated, summary counts

### Act 2 — Search (3 min)

1. Go to Dashboard
2. Paste a real JD (or natural language: "React developers in Bangalore with AWS and 5+ years")
3. Show results load in <1 second
4. Point to first result:
   - "87% match score (not magical, we'll explain it)"
   - "Match explanation bullets:" ✓ Has React + AWS skills, ✓ 3 yrs as Software Engineer, ✓ 5.5 yrs total
   - "This is the trust layer — you can see _why_ it matched, not just a score"
5. Scroll top 10, maybe click a card to see full profile

### Act 3 — Edit (1 min)

1. Click a candidate card → open profile
2. Change status dropdown from "New" to "Interview Scheduled"
3. Add note: "Strong MERN background, interviewed on [date], moved forward"
4. Show auto-save (no save button, just changes)
5. Go back to dashboard — filter by "Interview Scheduled" — show updated candidate still in list

### Act 4 — Export (30 sec)

1. Filter candidates by status (e.g., "Interview Scheduled")
2. Click "Export CSV"
3. Show CSV opened in Excel (candidate name, email, phone, current role, total experience, notes, etc.)

### Act 5 — Privacy (1 min)

1. Open a terminal on the laptop
2. Show `docker ps`: Qdrant + PostgreSQL running locally, no cloud services
3. Show `ps aux | grep ollama`: Ollama running locally
4. Explain: "Every candidate PDF, every embedding, every search query stays on this machine. No OpenAI, no Anthropic, no external AI service. In production, this runs entirely inside your cloud account."
5. Optionally: Disconnect WiFi, refresh frontend, show it still works (proves offline)

**Estimated total demo time:** 8 minutes

---

## PHASE 11: RISK LOG & MITIGATION

| Risk                                                          | Probability | Impact | Mitigation                                                                                          |
| ------------------------------------------------------------- | ----------- | ------ | --------------------------------------------------------------------------------------------------- |
| Parsing quality too low with Qwen2.5:3b                       | Medium      | High   | Pre-test on 5 PDFs on Day 1, escalate to Qwen2.5:7b or refinement by Day 2 noon                     |
| Qdrant + PostgreSQL performance degradation at 100 candidates | Low         | Medium | Add indexes on Day 1, load test on Day 5                                                            |
| BGE embedding quality insufficient for search relevance       | Low         | High   | Test on Day 3, have vector search + BM25 fallback + reranker ready                                  |
| FastAPI BackgroundTasks crashes on 100 concurrent uploads     | Low         | Medium | Switch to queue worker pattern if needed, but beta is 1 recruiter so concurrency expected to be low |
| Frontend build complexity (TypeScript + React SSR)            | Low         | Low    | Use Next.js scaffold to avoid build config work                                                     |
| Ollama model download fails or OOM on laptop                  | Medium      | High   | Pre-download on Day 0, have Mistral fallback model queued                                           |

---

## SUMMARY TABLE: All 15 Modules at a Glance

| #   | Module              | Size              | Day | Dep.     | Status                |
| --- | ------------------- | ----------------- | --- | -------- | --------------------- |
| 1   | Database & ORM      | 3–4h              | 1   | —        | Ready                 |
| 2   | Vector DB           | 2–3h              | 1   | —        | Ready                 |
| 3   | LLM + Prompts       | 4–5h              | 1–2 | 1,2      | Ready (iterate Day 2) |
| 4   | PDF Extraction      | 2–3h              | 1   | —        | Ready                 |
| 5   | Identity Resolution | 3–4h              | 2   | 1        | Ready                 |
| 6   | Skill Normalization | 2–3h              | 2   | 3        | Ready                 |
| 7   | Parsing Pipeline    | 4–5h              | 2   | 1–6      | Ready                 |
| 8   | Embeddings          | 2–3h              | 2   | 3        | Ready                 |
| 9   | Search & Matching   | 6–8h              | 3   | 1–8      | Ready (most complex)  |
| 10  | Upload API          | 3–4h              | 3   | 1,7      | Ready                 |
| 11  | CRUD API            | 4–5h              | 3   | 1,9      | Ready                 |
| 12  | Auth                | 1–2h              | 3   | —        | Ready (hardcoded)     |
| 13  | Frontend Infra      | 2–3h              | 4   | —        | Ready                 |
| 14  | Frontend Pages      | 12–15h            | 4   | 11,12,13 | Ready                 |
| 15  | Integration & QA    | 4–6h              | 5   | 1–14     | Ready                 |
|     |                     | **~60–70h total** |     |          | **Ready to build**    |

---

## NEXT STEPS: NOW BUILD IT

1. **Confirm** all Phase 1 environment checks are done (services running, models downloaded)
2. **Start Day 1** with Module 1 (PostgreSQL schema)
3. **Checkpoint after each Day** against the milestone gates above
4. **Escalate any gotchas** immediately (don't let parsing quality issues slip to Day 3)
5. **Demo ready by end of Day 5**

---

## Questions Before Build?

- Should we adjust the timeline based on your laptop specs (CPU model, RAM, available disk)?
- Do you have 100 real LinkedIn PDFs ready, or should we work with fewer during testing?
- Any specific recruiter requirements I've missed from the PRD or architecture docs?
- Should we add soft-delete / audit logging to the beta, or leave it for production?

**Ready to begin? Let's build this step by step.**
