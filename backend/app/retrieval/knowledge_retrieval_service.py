import asyncio
import re
import uuid

from qdrant_client.models import FieldCondition, Filter, MatchValue, PointStruct

from mystic_auth.redis.client import redis_client
from ..ai_integration.gemini_client import embed_text
from .exceptions import RetrievalError
from .qdrant_client import COLLECTION_NAME, get_client

_HEADING_RE = re.compile(r"^#{1,6}\s+.*$", re.MULTILINE)

# Same rationale as ai_integration/gemini_client.py's own
# _REQUEST_TIMEOUT_SECONDS: applied via asyncio.wait_for around every
# outbound Qdrant call so a stalled/unreachable Qdrant can't hang a request
# indefinitely.
_REQUEST_TIMEOUT_SECONDS = 15

# Guards index_knowledge_base's delete-then-upsert pair against a second
# concurrent re-index for the *same* user interleaving with it (e.g. a
# rapid double-submit of PUT /career-knowledge/) — without this, two
# racing calls could each delete the other's freshly-upserted points,
# leaving Qdrant reflecting neither save cleanly. A Redis lock (not an
# in-process asyncio.Lock) since the backend isn't assumed to run as a
# single process/replica. Postgres itself is never at risk — this only
# protects Qdrant's derived index (see index_knowledge_base's docstring).
_REINDEX_LOCK_TIMEOUT_SECONDS = 30


def _reindex_lock(user_id: int):
    return redis_client.lock(
        f"career_knowledge_reindex_lock:{user_id}",
        timeout=_REINDEX_LOCK_TIMEOUT_SECONDS,
    )


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
    Re-indexes a user's entire knowledge base: embeds the current chunk set,
    then deletes every existing chunk for this user and stores the new one.
    Deliberately embeds *before* deleting anything — chunks are embedded
    concurrently (one Gemini call per chunk, each independently subject to
    ai_integration's own timeout) rather than one at a time, and if any of
    them fails, nothing in Qdrant has been touched yet, so the previously
    indexed content keeps serving search exactly as before instead of the
    user's knowledge base going silently unsearchable. Re-indexing (rather
    than diffing old vs. new chunks) is still simpler and more correct than
    a diff — a shrinking section count would otherwise leave stale orphaned
    points — and knowledge bases are small enough that re-embedding on every
    save is cheap.
    """
    client = get_client()

    chunks = chunk_markdown(content)

    # Embedding (the slow, Gemini-calling part) happens outside the lock —
    # only the delete+upsert pair that actually touches shared Qdrant state
    # needs to be serialized per user.
    vectors = [] if not chunks else await asyncio.gather(*(embed_text(chunk) for chunk in chunks))

    async with _reindex_lock(user_id):
        if not chunks:
            # Nothing to index, but any previous content must still be cleared.
            await _call(
                client.delete(collection_name=COLLECTION_NAME, points_selector=_user_filter(user_id)), "delete"
            )
            return

        points = [
            PointStruct(
                id=_point_id(user_id, i),
                vector=vector,
                payload={"user_id": user_id, "chunk": chunk},
            )
            for i, (chunk, vector) in enumerate(zip(chunks, vectors))
        ]

        await _call(
            client.delete(collection_name=COLLECTION_NAME, points_selector=_user_filter(user_id)), "delete"
        )
        await _call(client.upsert(collection_name=COLLECTION_NAME, points=points), "upsert")


async def delete_knowledge_base(user_id: int) -> None:
    """Removes every indexed chunk for a user — called on knowledge base deletion.

    Uses the same per-user lock as index_knowledge_base so this can't race a
    concurrent re-index (e.g. delete landing between that call's own
    delete+upsert and leaving stale points behind, or vice versa).
    """
    client = get_client()
    async with _reindex_lock(user_id):
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
