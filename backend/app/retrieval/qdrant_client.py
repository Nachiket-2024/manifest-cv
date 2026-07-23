from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams

from mystic_auth.sdk import settings
from ..ai_integration.gemini_client import EMBEDDING_DIMENSIONS

# One shared collection for every user's career knowledge chunks, isolated
# per-user via a payload filter (see knowledge_retrieval_service.py) rather
# than one collection per user — Qdrant collections are a heavier unit than
# that, and per-user filtering scales fine at this data size.
COLLECTION_NAME = "career_knowledge_chunks"

_client: AsyncQdrantClient | None = None


def get_client() -> AsyncQdrantClient:
    global _client
    if _client is None:
        _client = AsyncQdrantClient(url=settings.QDRANT_URL)
    return _client


async def ensure_collection() -> None:
    """
    Creates the shared collection if it doesn't already exist. Called once
    at app startup (see main.py's lifespan) — idempotent, safe on every
    restart.
    """
    client = get_client()
    if not await client.collection_exists(COLLECTION_NAME):
        await client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=EMBEDDING_DIMENSIONS, distance=Distance.COSINE),
        )


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
