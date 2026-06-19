from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.vector_db import init_qdrant_collection
from app.embeddings.generator import load_models
from app.llm.client import warmup as warmup_llm
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — initializing Qdrant collection and loading models...")
    await init_qdrant_collection()
    load_models()
    await warmup_llm()
    logger.info("Models loaded, ready to serve.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="AI Recruitment Intelligence Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.routes import auth, upload, candidates, search, export  # noqa: E402

app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(upload.router, prefix="/api/v1", tags=["upload"])
app.include_router(candidates.router, prefix="/api/v1", tags=["candidates"])
app.include_router(search.router, prefix="/api/v1", tags=["search"])
app.include_router(export.router, prefix="/api/v1", tags=["export"])


@app.get("/health")
async def health():
    return {"status": "ok"}
