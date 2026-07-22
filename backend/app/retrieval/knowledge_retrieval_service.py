import asyncio
import re
import uuid

from qdrant_client.models import FieldCondition, Filter, MatchValue, PointStruct

from ..ai_integration.gemini_client import embed_text
from .exceptions import RetrievalError
from .qdrant_client import COLLECTION_NAME, get_client

_HEADING_RE = re.compile(r"^#{1,6}\s+.*$", re.MULTILINE)

# Same rationale as ai_integration/gemini_client.py's own
# _REQUEST_TIMEOUT_SECONDS: applied via asyncio.wait_for around every
# outbound Qdrant call so a stalled/unreachable Qdrant can't hang a request
# indefinitely.
_REQUEST_TIMEOUT_SECONDS = 15


async def _call(coro, action: str):
    """
    Shared plumbing for every outbound Qdrant call — keeps timeout/error
    semantics (RetrievalError) consistent across delete/upsert/query_points,
    the same way ai_integration.gemini_client._generate_text does for Gemini.
    """
    try:
        return await asyncio.wait_for(coro, timeout=_REQUEST_TIMEOUT_SECONDS)
    except asyncio.TimeoutError as exc:
        raise RetrievalError(f"Qdrant {action} did not respond within {_REQUEST_TIMEOUT_SECONDS}s") from exc
    except Exception as exc:
        raise RetrievalError(f"Qdrant {action} failed: {exc}") from exc


def chunk_markdown(content: str) -> list[str]:
    """
    Splits structured Markdown into per-section chunks on headings, so
    semantic search (Phase 2's job-description matching) can retrieve a
    relevant section — e.g. "Skills" — instead of the whole knowledge base
    at once. Falls back to the whole document as a single chunk if it has
    no headings at all (e.g. a single-paragraph dump).
    """
    positions = [m.start() for m in _HEADING_RE.finditer(content)]
    if not positions:
        stripped = content.strip()
        return [stripped] if stripped else []

    chunks = []
    for i, start in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(content)
        chunk = content[start:end].strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def _point_id(user_id: int, chunk_index: int) -> str:
    # Deterministic, so re-indexing overwrites the same points rather than
    # accumulating duplicates for a user whose chunk count stays the same.
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"career_knowledge:{user_id}:{chunk_index}"))


def _user_filter(user_id: int) -> Filter:
    return Filter(must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))])


async def index_knowledge_base(user_id: int, content: str) -> None:
    """
    Re-indexes a user's entire knowledge base: deletes every existing chunk
    for this user, then embeds and stores the current chunk set. Simpler
    and more correct than diffing old vs. new chunks — a shrinking section
    count would otherwise leave stale orphaned points — and knowledge bases
    are small enough that re-embedding on every save is cheap.
    """
    client = get_client()

    await _call(
        client.delete(collection_name=COLLECTION_NAME, points_selector=_user_filter(user_id)), "delete"
    )

    chunks = chunk_markdown(content)
    if not chunks:
        return

    points = [
        PointStruct(
            id=_point_id(user_id, i),
            vector=await embed_text(chunk),
            payload={"user_id": user_id, "chunk": chunk},
        )
        for i, chunk in enumerate(chunks)
    ]

    await _call(client.upsert(collection_name=COLLECTION_NAME, points=points), "upsert")


async def delete_knowledge_base(user_id: int) -> None:
    """Removes every indexed chunk for a user — called on knowledge base deletion."""
    client = get_client()
    await _call(
        client.delete(collection_name=COLLECTION_NAME, points_selector=_user_filter(user_id)), "delete"
    )


async def search_knowledge_base(user_id: int, query: str, top_k: int = 5) -> list[dict]:
    """
    Semantic search scoped to one user's own chunks — every query is
    filtered by user_id server-side, so it can never return another user's
    knowledge base content. Powers Phase 2's job-description matching;
    exposed now as its own endpoint mainly so retrieval can be verified
    independently of that later work.
    """
    client = get_client()
    query_vector = await embed_text(query)

    results = await _call(
        client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            query_filter=_user_filter(user_id),
            limit=top_k,
        ),
        "query_points",
    )

    return [{"chunk": point.payload["chunk"], "score": point.score} for point in results.points]
