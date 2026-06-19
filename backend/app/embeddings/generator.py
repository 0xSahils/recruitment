from sentence_transformers import SentenceTransformer, CrossEncoder
from app.config import settings
import logging
import numpy as np

logger = logging.getLogger(__name__)

_embed_model: SentenceTransformer | None = None
_reranker_model: CrossEncoder | None = None


def load_models():
    global _embed_model, _reranker_model
    logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
    _embed_model = SentenceTransformer(settings.EMBEDDING_MODEL)
    logger.info(f"Loading reranker model: {settings.RERANKER_MODEL}")
    _reranker_model = CrossEncoder(settings.RERANKER_MODEL)
    logger.info("All ML models loaded.")


def get_embed_model() -> SentenceTransformer:
    global _embed_model
    if _embed_model is None:
        _embed_model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _embed_model


def get_reranker_model() -> CrossEncoder:
    global _reranker_model
    if _reranker_model is None:
        _reranker_model = CrossEncoder(settings.RERANKER_MODEL)
    return _reranker_model


def compose_candidate_text(candidate_data: dict) -> str:
    parts = []
    identity = candidate_data.get("identity", {})
    if identity.get("full_name"):
        parts.append(identity["full_name"])
    if identity.get("headline"):
        parts.append(identity["headline"])
    if candidate_data.get("summary"):
        parts.append(candidate_data["summary"])

    for exp in candidate_data.get("experience", []):
        exp_text = f"{exp.get('role', '')} at {exp.get('company', '')}"
        if exp.get("description"):
            exp_text += f": {exp['description']}"
        parts.append(exp_text)

    skills = candidate_data.get("skills", {})
    normalized = skills.get("normalized", [])
    original = skills.get("original", [])
    all_skills = list(set(normalized + original))
    if all_skills:
        parts.append("Skills: " + ", ".join(all_skills))

    for edu in candidate_data.get("education", []):
        edu_text = f"{edu.get('degree', '')} in {edu.get('field', '')} from {edu.get('institution', '')}"
        parts.append(edu_text)

    return " | ".join(filter(None, parts))


def generate_embedding(text: str) -> list[float]:
    model = get_embed_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    model = get_embed_model()
    embeddings = model.encode(texts, normalize_embeddings=True, batch_size=32)
    return embeddings.tolist()


def rerank(query: str, documents: list[str], top_n: int | None = None) -> list[tuple[int, float]]:
    model = get_reranker_model()
    pairs = [[query, doc] for doc in documents]
    scores = model.predict(pairs)
    indexed = list(enumerate(scores))
    indexed.sort(key=lambda x: x[1], reverse=True)
    if top_n:
        indexed = indexed[:top_n]
    return [(idx, float(score)) for idx, score in indexed]
