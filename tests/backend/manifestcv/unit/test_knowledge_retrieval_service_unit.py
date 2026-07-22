# tests/backend/manifestcv/unit/test_knowledge_retrieval_service_unit.py
#
# Covers retrieval/knowledge_retrieval_service.py's own error-handling
# logic directly (unlike the manifestcv integration suites, which mock this
# module's public functions wholesale at each route's import site and so
# never actually exercise this code) — specifically the RetrievalError
# wrapping/timeout behavior added around every outbound Qdrant call.
import asyncio

import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.app.retrieval.exceptions import RetrievalError
from backend.app.retrieval import knowledge_retrieval_service as service

MODULE = "backend.app.retrieval.knowledge_retrieval_service"


def _fake_client():
    return MagicMock(
        delete=AsyncMock(),
        upsert=AsyncMock(),
        query_points=AsyncMock(),
    )


class _FakePoint:
    def __init__(self, chunk: str, score: float):
        self.payload = {"chunk": chunk}
        self.score = score


class _FakeQueryResult:
    def __init__(self, points):
        self.points = points


def test_chunk_markdown_splits_on_headings():
    content = "# Skills\nPython, SQL\n\n## Projects\nBuilt a thing"
    chunks = service.chunk_markdown(content)
    assert chunks == ["# Skills\nPython, SQL", "## Projects\nBuilt a thing"]


def test_chunk_markdown_falls_back_to_whole_document_with_no_headings():
    assert service.chunk_markdown("Just a paragraph, no headings.") == ["Just a paragraph, no headings."]


def test_chunk_markdown_returns_empty_list_for_blank_content():
    assert service.chunk_markdown("   \n  ") == []


@pytest.mark.asyncio
async def test_index_knowledge_base_wraps_qdrant_delete_failure_as_retrieval_error(mocker):
    client = _fake_client()
    client.delete.side_effect = ConnectionError("qdrant unreachable")
    mocker.patch(f"{MODULE}.get_client", return_value=client)

    with pytest.raises(RetrievalError, match="delete failed"):
        await service.index_knowledge_base(1, "# Section\ncontent")


@pytest.mark.asyncio
async def test_index_knowledge_base_wraps_qdrant_upsert_failure_as_retrieval_error(mocker):
    client = _fake_client()
    mocker.patch(f"{MODULE}.get_client", return_value=client)
    mocker.patch(f"{MODULE}.embed_text", new_callable=AsyncMock, return_value=[0.1, 0.2])
    client.upsert.side_effect = ConnectionError("qdrant unreachable")

    with pytest.raises(RetrievalError, match="upsert failed"):
        await service.index_knowledge_base(1, "# Section\ncontent")


@pytest.mark.asyncio
async def test_index_knowledge_base_skips_upsert_for_empty_content(mocker):
    client = _fake_client()
    mocker.patch(f"{MODULE}.get_client", return_value=client)

    await service.index_knowledge_base(1, "   ")

    client.delete.assert_awaited_once()
    client.upsert.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_knowledge_base_wraps_qdrant_failure_as_retrieval_error(mocker):
    client = _fake_client()
    client.delete.side_effect = RuntimeError("qdrant down")
    mocker.patch(f"{MODULE}.get_client", return_value=client)

    with pytest.raises(RetrievalError, match="delete failed"):
        await service.delete_knowledge_base(1)


@pytest.mark.asyncio
async def test_search_knowledge_base_wraps_qdrant_failure_as_retrieval_error(mocker):
    client = _fake_client()
    client.query_points.side_effect = RuntimeError("qdrant down")
    mocker.patch(f"{MODULE}.get_client", return_value=client)
    mocker.patch(f"{MODULE}.embed_text", new_callable=AsyncMock, return_value=[0.1, 0.2])

    with pytest.raises(RetrievalError, match="query_points failed"):
        await service.search_knowledge_base(1, "python backend")


@pytest.mark.asyncio
async def test_search_knowledge_base_returns_chunks_and_scores_on_success(mocker):
    client = _fake_client()
    client.query_points.return_value = _FakeQueryResult(
        [_FakePoint("Worked on backend systems.", 0.9)]
    )
    mocker.patch(f"{MODULE}.get_client", return_value=client)
    mocker.patch(f"{MODULE}.embed_text", new_callable=AsyncMock, return_value=[0.1, 0.2])

    results = await service.search_knowledge_base(1, "python backend", top_k=3)

    assert results == [{"chunk": "Worked on backend systems.", "score": 0.9}]
    client.query_points.assert_awaited_once()


@pytest.mark.asyncio
async def test_qdrant_call_wraps_timeout_as_retrieval_error(mocker):
    mocker.patch(f"{MODULE}._REQUEST_TIMEOUT_SECONDS", 0.01)

    async def _never_returns():
        await asyncio.sleep(1)

    with pytest.raises(RetrievalError, match="did not respond within"):
        await service._call(_never_returns(), "delete")
