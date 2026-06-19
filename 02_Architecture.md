# Technical Architecture Document

## Privacy Boundary — Read This First
Every component below runs on infrastructure the client controls (developer's laptop for beta, Azure VM for production). No component in this stack calls an external AI API. If any AI agent building this introduces an OpenAI/Anthropic/Cohere/Vectara API call, that is a constraint violation — flag it and stop.

---

## System Diagram (textual)

```
┌─────────────────────────────────────────────────────────┐
│  FRONTEND — React + shadcn/ui + Tailwind                 │
│  (recruiter dashboard, upload UI, candidate profile UI)  │
└───────────────────────┬───────────────────────────────────┘
                         │ REST API (JSON)
┌───────────────────────▼───────────────────────────────────┐
│  BACKEND — FastAPI (Python)                                │
│  ├─ Upload endpoint → async parsing queue                  │
│  ├─ Search endpoint → matching pipeline                     │
│  ├─ Candidate CRUD endpoints                                │
│  └─ Identity resolution + version tracking logic            │
└─────┬──────────────┬──────────────┬────────────────────────┘
      │              │              │
┌─────▼─────┐  ┌─────▼──────┐  ┌────▼─────────────┐
│ PostgreSQL │  │   Qdrant    │  │  Local AI Models   │
│ (structured│  │ (vector DB) │  │  via Ollama:        │
│  candidate │  │             │  │  - Qwen2.5 (LLM)     │
│  data)     │  │             │  │  - BGE-small (embed) │
│            │  │             │  │  - BGE-reranker-v2-m3│
└────────────┘  └─────────────┘  └───────────────────────┘
```

---

## Frontend

| Layer | Choice | Reason |
|---|---|---|
| Framework | React (via Next.js) | Developer's existing stack, fast iteration |
| UI components | shadcn/ui | Pre-built, professional-looking, fast to assemble for a client demo |
| Styling | Tailwind CSS | Pairs natively with shadcn/ui |
| Server state | TanStack Query | Handles async upload status, search loading states, cache invalidation on edit |
| Tables | TanStack Table | Candidate list view, sortable/filterable without extra backend work |

---

## Backend

**Framework: FastAPI (Python)**

Reason:
- Native Python ecosystem overlap with PDF parsing (PyMuPDF) and AI libraries (sentence-transformers, FlagEmbedding for BGE)
- Async support needed for background PDF processing jobs
- Fast to develop against for a 3–5 day build window

**Background job handling:** Use FastAPI's `BackgroundTasks` for beta (100 PDFs, simple). For production scale (10,000+), upgrade to a proper queue (Celery + Redis, or RQ) — architecture should isolate the parsing logic so this swap doesn't touch business logic.

---

## Database

**Primary Database: PostgreSQL**

Reason:
- Production-ready, well-understood, supports the relational structure needed for Candidate → Experience → Education → Skills (see `03_DatabaseDesign.md`)
- Scales comfortably past 10,000 candidates with proper indexing
- JSONB columns allow storing raw extracted data alongside structured fields (see "Future-Proof Extraction" principle below)

**Vector Database: Qdrant**

Reason:
- Supports metadata filtering combined with vector search in a single query (critical for Stage 1 + Stage 2 of the matching pipeline — see `04_AIMatchingSpec.md`)
- Runs locally with zero external dependency (Docker container or even embedded mode for beta)
- Production-grade, scales to millions of vectors if the platform grows

---

## PDF Processing

**PyMuPDF (fitz)**

Reason:
- Best raw text + layout extraction quality for LinkedIn PDF exports specifically (consistent column/section structure)
- Pure Python, no external service call, fast on CPU
- Used as the first-pass extractor; structured field extraction happens via the local LLM afterward (see AI Layer below)

---

## AI Layer — All Self-Hosted via Ollama

| Function | Model | Reason |
|---|---|---|
| Parsing (PDF text → structured JSON) | Qwen2.5 7B (beta: 3B if laptop struggles) | Strong instruction-following for structured JSON output, runs on CPU acceptably at 3B–7B size, fully local via Ollama |
| Embeddings | BGE-small-en-v1.5 | Lightweight (~130MB), strong retrieval quality for its size, CPU-friendly, self-hostable via `sentence-transformers` or Ollama |
| Reranking | BGE-reranker-v2-m3 | Best quality/latency/license balance for self-hosted rerankers as of 2026 benchmarks. ~145ms CPU latency at base size — acceptable for a few hundred candidates. Apache 2.0 licensed, no API cost. |

**Why not GPT-4.1 Mini / Gemini 2.5 Flash for parsing (as originally considered):** Both are cloud APIs. They would violate the no-third-party-AI constraint the moment a real candidate PDF is sent to them. They are mentioned in earlier drafts only as a reference for parsing quality — they must not be used with real candidate data. If parsing quality with Qwen2.5 proves insufficient during testing, the fallback is a larger local model (e.g. Qwen2.5 14B on the production VM), not a cloud API.

---

## Deployment

| Phase | Where | Notes |
|---|---|---|
| Beta / Demo | Developer's laptop (16GB RAM, i5, no GPU) | Use smaller model variants (Qwen2.5:3b, BGE-small). Docker Compose for Postgres + Qdrant only — Ollama runs natively, not in Docker, for better CPU performance. |
| Production | Azure VM — Standard D4s v3 (4 vCPU, 16GB RAM), Central India region | ~₹8,000–10,600/month (1-year reserved). Upgrade to Qwen2.5:7b or 14b once on proper hardware. See cost breakdown in `07_DevelopmentPlan.md`. |

---

## API Layer
All frontend-backend communication via REST, JSON payloads. Full contract in `05_APIContracts.md`. No GraphQL — unnecessary complexity for this scope.

## Authentication (Beta)
Single hardcoded recruiter login, session cookie. Production phase adds proper multi-user auth (out of scope for this document set — flag as a Phase 2 requirement when production planning begins).
