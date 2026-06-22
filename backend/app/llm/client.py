import httpx
import logging
from app.config import settings

logger = logging.getLogger(__name__)

_client: httpx.AsyncClient | None = None


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        # Increased timeout to 600 seconds (10 minutes) for slower CPU-only local environments
        _client = httpx.AsyncClient(base_url=settings.OLLAMA_BASE_URL, timeout=600.0)
    return _client


async def generate(prompt: str, system: str = "", model: str | None = None) -> str:
    client = get_client()
    payload = {
        "model": model or settings.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.1, "num_predict": 2048, "num_ctx": 8192},
    }
    if system:
        payload["system"] = system

    resp = await client.post("/api/generate", json=payload)
    resp.raise_for_status()
    data = resp.json()
    return data.get("response", "")


async def warmup():
    logger.info("Warming up Ollama model...")
    try:
        await generate("Return empty JSON: {}", system="You are a test.")
        logger.info("Ollama warm-up complete.")
    except Exception as e:
        logger.warning(f"Ollama warm-up failed (will retry on first real call): {e}")
