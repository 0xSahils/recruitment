from qdrant_client import QdrantClient, models
from app.config import settings
import logging

logger = logging.getLogger(__name__)

qdrant = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)


async def init_qdrant_collection():
    collections = qdrant.get_collections().collections
    exists = any(c.name == settings.QDRANT_COLLECTION for c in collections)
    if not exists:
        qdrant.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=models.VectorParams(
                size=settings.EMBEDDING_DIM,
                distance=models.Distance.COSINE,
            ),
        )
        logger.info(f"Created Qdrant collection '{settings.QDRANT_COLLECTION}' with dim={settings.EMBEDDING_DIM}")
    else:
        logger.info(f"Qdrant collection '{settings.QDRANT_COLLECTION}' already exists.")


def upsert_candidate_vector(candidate_id: str, embedding: list[float], metadata: dict):
    qdrant.upsert(
        collection_name=settings.QDRANT_COLLECTION,
        points=[
            models.PointStruct(
                id=candidate_id,
                vector=embedding,
                payload=metadata,
            )
        ],
    )


def search_vectors(query_embedding: list[float], filters: models.Filter | None = None, limit: int = 100) -> list:
    return qdrant.query_points(
        collection_name=settings.QDRANT_COLLECTION,
        query=query_embedding,
        query_filter=filters,
        limit=limit,
        with_payload=True,
    ).points


def delete_candidate_vector(candidate_id: str):
    qdrant.delete(
        collection_name=settings.QDRANT_COLLECTION,
        points_selector=models.PointIdsList(points=[candidate_id]),
    )
