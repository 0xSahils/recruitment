# AI Recruitment Intelligence Platform — Setup Guide

> Last updated: 2026-06-23

---

## PREREQUISITES

- **Windows 10/11**
- **Docker Desktop** — https://www.docker.com/products/docker-desktop/
- **Node.js 18+** — https://nodejs.org/
- **Ollama** — https://ollama.com/download
- **Python 3.11** — ⚠️ **MUST be 3.11, NOT 3.12/3.13/3.14** (torch/sentence-transformers break on newer versions)
  - Download: https://www.python.org/downloads/release/python-3119/
  - Scroll down → **Windows installer (64-bit)**
  - ✅ Check **"Add Python 3.11 to PATH"** during install

---

## Step 1: Start Docker Services

Open a terminal in the project root (where `docker-compose.yml` is):

```bash
docker compose up -d
```

Verify:
```bash
docker ps
```
You should see `recruit_postgres` and `recruit_qdrant` running.

---

## Step 2: Install Ollama + Pull Model

1. Install Ollama from https://ollama.com/download
2. Open a terminal:
```bash
ollama pull qwen2.5:3b
```
3. Verify: `ollama list` should show `qwen2.5:3b`

---

## Step 3: Setup Backend (Python)

Open a terminal in the `backend/` folder:

```bash
# If you have multiple Python versions, use py -3.11 explicitly
py -3.11 -m venv venv

# Activate the venv
venv\Scripts\activate

# Verify — MUST show 3.11.x
python --version

# Install all dependencies (~5-10 min, downloads torch ~2.5GB)
pip install -r requirements.txt
```

> **If torch fails:** run this first, then retry:
> ```bash
> pip install torch --index-url https://download.pytorch.org/whl/cpu
> pip install -r requirements.txt
> ```

### Run Database Migration
```bash
alembic upgrade head
```

### Start Backend
```bash
python run.py
```

First startup takes 30-60 seconds (downloads embedding + reranker models ~1.1GB total).
Wait until you see:
```
INFO:app.main:Models loaded, ready to serve.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Health check: open http://localhost:8000/health → `{"status": "ok"}`

---

## Step 4: Setup Frontend (Next.js)

Open a **NEW** terminal in the `frontend/` folder:

```bash
npm install
npm run dev
```

You should see:
```
▲ Next.js 15.x
- Local: http://localhost:3000
```

---

## Step 5: Use the App

1. Open http://localhost:3000
2. Login: **demo** / **demo123**
3. Upload → drag LinkedIn PDFs → watch progress
4. Dashboard → search for candidates
5. Click a candidate → view/edit profile

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: No module named 'torch'` | Wrong Python version. Delete `venv/`, recreate with `py -3.11 -m venv venv` |
| `KeyboardInterrupt` during startup | Wrong Python version (3.14). Must use 3.11 |
| `connection refused` on port 5435 | Docker not running. Run `docker compose up -d` |
| Backend hangs on first search | Reranker model downloading. Wait 1-2 minutes |
| `Ollama warm-up failed` | Ollama not running. Open Ollama app or run `ollama serve`. Non-fatal warning — search still works |
| `ECONNRESET` / 500 on search | Backend crashed or restarting. Check the backend terminal for errors |

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
