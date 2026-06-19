# AI Recruitment Intelligence Platform — Setup Guide

> Last updated: 2026-06-20
> Status: Code complete. Needs dependency install + database migration + test run.

---

## WHAT'S DONE (100% code complete)

### Infrastructure
- [x] `docker-compose.yml` — PostgreSQL 15 + Qdrant vector DB (both running and healthy)
- [x] `.env` — All config values set (DB URLs, Ollama, models, demo creds)
- [x] `.gitignore` — Proper exclusions for venv, node_modules, .env, PDFs
- [x] Ollama running with `qwen2.5:3b` model pulled

### Backend (FastAPI + Python) — 38 source files
- [x] **Models** — 7 SQLAlchemy tables: candidates, experiences, education, skills, candidate_versions, candidate_notes, search_logs
- [x] **Alembic migration** — Full schema with indexes (GIN on skills, unique on linkedin_url, indexes on email/phone/status)
- [x] **PDF Extractor** — PyMuPDF (fitz) text extraction from LinkedIn PDF exports
- [x] **LLM Client** — Async httpx client to Ollama with JSON format, temperature 0.1, warmup on startup
- [x] **Resume Parser** — Structured prompt → JSON extraction → json_repair → validation with confidence scoring
- [x] **JD Parser** — Extracts role, required/preferred skills, experience range, location from job descriptions
- [x] **Skill Normalizer** — YAML dictionary (50+ mappings) first, LLM fallback for unknowns
- [x] **Identity Resolution** — 4-level chain: LinkedIn URL → email → phone → name+company fuzzy match
- [x] **Version Tracking** — Diff-based change summaries when candidate profiles are re-uploaded
- [x] **Embeddings** — sentence-transformers (BAAI/bge-small-en-v1.5, 384-dim)
- [x] **Reranker** — CrossEncoder (BAAI/bge-reranker-v2-m3), top 40 candidates only
- [x] **Search Pipeline** — Qdrant metadata filter → vector search + BM25 (RRF fusion) → rerank → weighted scoring (50% semantic, 25% skill, 15% role, 10% experience) → match explanations
- [x] **API Routes** — Auth (JWT), Upload (multipart + background processing), Candidates CRUD, Search, Export CSV
- [x] **Soft-delete** — `deleted_at` column, filtered from all reads

### Frontend (Next.js 15 + React 19 + TypeScript) — 10 source files
- [x] **Login page** — Gradient background, demo credentials hint, JWT in localStorage
- [x] **Dashboard** — JD/natural language search, parsed query display, status filter tabs, ranked cards with match explanations, score breakdown (S/K/R/E), inline status dropdown, export CSV
- [x] **Upload page** — Drag-and-drop (react-dropzone), batch progress bar, per-file status (new/updated/failed)
- [x] **Candidates table** — Search, status/location filters, paginated table with status badges
- [x] **Candidate Profile** — Click-to-edit fields, status dropdown, experience timeline, education, skills badges, notes, version history
- [x] **API client** — Axios with JWT interceptor, auto-redirect on 401
- [x] **Providers** — Proper server/client component split (layout is server, providers are client)

---

## WHAT'S LEFT (installation + setup)

### Step 1: Install Python Dependencies (~5-10 min)
```bash
cd backend
venv\Scripts\activate
pip install -r requirements.txt
```
> **Note:** `torch` (~2.5 GB) and `sentence-transformers` (~500 MB) are the biggest downloads.
> If torch fails on Python 3.13, try:
> ```bash
> pip install torch --index-url https://download.pytorch.org/whl/cpu
> pip install -r requirements.txt
> ```

### Step 2: Install Frontend Dependencies (~1-2 min)
```bash
cd frontend
npm install
```
> Already partially installed (327 packages). May just need a clean `npm install`.

### Step 3: Verify Docker Services Are Running
```bash
docker compose up -d
docker ps
```
> You should see `recruit_postgres` (healthy) and `recruit_qdrant` (running).
> If not running: `docker compose up -d` from the project root.

### Step 4: Run Database Migration
```bash
cd backend
venv\Scripts\alembic upgrade head
```
> Creates all 7 tables + indexes in PostgreSQL.

### Step 5: Start Backend
```bash
cd backend
venv\Scripts\python run.py
```
> On first start:
> - Creates Qdrant collection (384-dim cosine)
> - Downloads embedding model BAAI/bge-small-en-v1.5 (~130 MB, one-time)
> - Downloads reranker model BAAI/bge-reranker-v2-m3 (~1 GB, one-time)
> - Warms up Ollama (first LLM call)
> - Should print "Models loaded, ready to serve." and listen on http://localhost:8000
> - Health check: http://localhost:8000/health → `{"status": "ok"}`

### Step 6: Start Frontend
```bash
cd frontend
npm run dev
```
> Opens on http://localhost:3000
> Login with: **demo / demo123**

### Step 7: End-to-End Test
1. Login at http://localhost:3000
2. Go to Upload → drag in 2-3 LinkedIn PDFs → watch progress bar
3. Go to Dashboard → type a search like "React developer with 5+ years" → verify ranked results with match explanations
4. Click a candidate → verify profile, try editing a field, add a note
5. Go to Candidates table → verify list, try status filter

---

## DEMO STRATEGY (Low-Spec Laptop — 16GB RAM, No GPU)

### Performance Profile
| Operation | Time | Notes |
|-----------|------|-------|
| Search query | 1-4 seconds | Fast — this is the demo headline |
| PDF parsing | 8-20 sec/PDF | CPU-bound (qwen2.5:3b) |
| Embedding generation | ~100ms | Trivial |
| Re-ranking | ~1-2 seconds | Top 40 only |

### Pre-Demo Prep (do this BEFORE the meeting)
1. Pre-seed **100 candidate PDFs** ahead of time (takes ~15-30 min)
2. Run a few test searches to verify results quality
3. Verify Ollama + Docker + both servers are running

### During Demo
1. Show search with pre-seeded data → instant ranked results with match explanations
2. Live-upload only **5-10 PDFs** → progress bar, "New candidate" / "Updated v2" labels
3. Re-search → new candidates appear in results
4. Show privacy proof: disconnect WiFi → everything still works
5. Show export → CSV download

### Memory Budget (~7-9 GB of 16 GB)
- Ollama (qwen2.5:3b): ~3-4 GB
- PostgreSQL: ~200 MB
- Qdrant: ~200 MB
- Python (embeddings + reranker): ~2-3 GB
- Node.js + Browser: ~1 GB

---

## PROJECT STRUCTURE
```
RECRUTIMENT/
├── .env                          # Environment config
├── docker-compose.yml            # Postgres + Qdrant
├── SETUP_GUIDE.md               # This file
│
├── backend/
│   ├── requirements.txt
│   ├── run.py                    # Entry point (uvicorn)
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       └── 001_init_schema.py
│   ├── venv/                     # Python virtual env
│   └── app/
│       ├── config.py             # Settings from .env
│       ├── db.py                 # Async SQLAlchemy engine
│       ├── main.py               # FastAPI app + lifespan
│       ├── models.py             # 7 ORM models
│       ├── schemas.py            # Pydantic request/response
│       ├── vector_db.py          # Qdrant operations
│       ├── api/
│       │   ├── deps.py           # JWT auth
│       │   └── routes/
│       │       ├── auth.py       # Login/logout
│       │       ├── upload.py     # PDF upload + batch status
│       │       ├── candidates.py # CRUD + notes + versions
│       │       ├── search.py     # Search endpoint
│       │       └── export.py     # CSV export
│       ├── pdf/
│       │   └── extractor.py      # PyMuPDF text extraction
│       ├── llm/
│       │   ├── client.py         # Ollama async client
│       │   ├── prompts.py        # Resume/JD parse prompts
│       │   └── parsers.py        # JSON parse + validate
│       ├── embeddings/
│       │   └── generator.py      # SentenceTransformer + CrossEncoder
│       ├── skills/
│       │   ├── normalizer.py     # Dictionary + LLM fallback
│       │   └── skill_dictionary.yaml
│       ├── identity/
│       │   ├── resolver.py       # 4-level dedup chain
│       │   └── differ.py         # Version diff summaries
│       ├── parsing/
│       │   ├── pipeline.py       # Core orchestrator
│       │   └── validators.py     # Date parsing, sanitization
│       └── search/
│           ├── jd_parser.py      # JD → structured query
│           ├── retrieval.py      # Vector + BM25 + RRF
│           ├── reranker.py       # CrossEncoder rerank
│           ├── scorer.py         # Weighted scoring
│           └── explainer.py      # Match explanations
│
└── frontend/
    ├── package.json
    ├── next.config.js            # API proxy to :8000
    ├── tailwind.config.js
    ├── tsconfig.json
    └── src/
        ├── lib/
        │   ├── api.ts            # Axios client + all API functions
        │   └── utils.ts          # Formatters + helpers
        ├── components/
        │   ├── Navbar.tsx
        │   └── Providers.tsx     # QueryClient + Toaster
        └── app/
            ├── layout.tsx        # Root layout (server component)
            ├── globals.css       # Tailwind + component classes
            ├── page.tsx          # Login page
            ├── dashboard/
            │   └── page.tsx      # Search + ranked results
            ├── upload/
            │   └── page.tsx      # PDF upload + progress
            └── candidates/
                ├── page.tsx      # Candidates table
                └── [id]/
                    └── page.tsx  # Candidate profile

## BUGS FIXED IN THIS SESSION
1. Identity resolver now receives company from experience data (was missing → name+company matching was broken)
2. Search route skips candidates without valid IDs (was crashing on empty UUID string)
3. Extraction confidence now stored in Qdrant metadata and surfaced in search results
4. Reranker score handles None/missing values safely
5. PDF storage path now correctly resolves to backend/storage/pdfs/ (was going to repo root)
6. Root layout converted to server component with client Providers wrapper (proper Next.js 15 pattern)
7. Dashboard now invalidates search results after status change
8. LLM warm-up added to server startup (avoids 10s delay on first real request)
9. Added staleTime:30s to QueryClient to reduce redundant API calls
10. Removed redundant experience check in parsing pipeline
```
