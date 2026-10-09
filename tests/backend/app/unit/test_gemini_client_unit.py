import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.ai_integration import gemini_client
from backend.app.ai_integration.exceptions import AIIntegrationError


def _client(response=None):
    models = MagicMock(
        generate_content=AsyncMock(return_value=response),
        embed_content=AsyncMock(return_value=response),
    )
    return MagicMock(aio=SimpleNamespace(models=models))


@pytest.mark.asyncio
async def test_generate_text_strips_response_text_and_passes_model_and_prompt(mocker):
    client = _client(SimpleNamespace(text="  Generated resume\n"))
    mocker.patch.object(gemini_client, "_get_client", return_value=client)

    result = await gemini_client.generate_resume("Python role", ["Python experience"])

    assert result == "Generated resume"
    client.aio.models.generate_content.assert_awaited_once()
    call = client.aio.models.generate_content.await_args
    assert call.kwargs["model"] == gemini_client.settings.GEMINI_MODEL
    assert "Python role" in call.kwargs["contents"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "message"),
    [
        (SimpleNamespace(text=""), "empty generated resume"),
        (SimpleNamespace(text=None), "empty generated resume"),
    ],
)
async def test_generate_text_rejects_empty_responses(mocker, response, message):
    mocker.patch.object(gemini_client, "_get_client", return_value=_client(response))

    with pytest.raises(AIIntegrationError, match=message):
        await gemini_client.generate_resume("role", [])


@pytest.mark.asyncio
async def test_generate_text_wraps_sdk_errors(mocker):
    client = _client()
    client.aio.models.generate_content.side_effect = RuntimeError("provider unavailable")
    mocker.patch.object(gemini_client, "_get_client", return_value=client)

    with pytest.raises(AIIntegrationError, match="provider unavailable"):
        await gemini_client.structure_knowledge_base("raw notes")


@pytest.mark.asyncio
async def test_generate_text_wraps_timeout(mocker):
    client = _client()
    client.aio.models.generate_content.side_effect = asyncio.TimeoutError
    mocker.patch.object(gemini_client, "_get_client", return_value=client)
    mocker.patch.object(gemini_client, "_REQUEST_TIMEOUT_SECONDS", 0.01)

    with pytest.raises(AIIntegrationError, match="did not respond within"):
        await gemini_client.refine_resume("role", [], "old", "shorter")


@pytest.mark.asyncio
async def test_embed_text_returns_values_and_configures_dimensions(mocker):
    embedding = SimpleNamespace(values=[0.1, 0.2])
    client = _client(SimpleNamespace(embeddings=[embedding]))
    mocker.patch.object(gemini_client, "_get_client", return_value=client)

    assert await gemini_client.embed_text("Python") == [0.1, 0.2]
    call = client.aio.models.embed_content.await_args
    assert call.kwargs["model"] == gemini_client.settings.GEMINI_EMBEDDING_MODEL
    assert call.kwargs["contents"] == "Python"
    assert call.kwargs["config"].output_dimensionality == gemini_client.EMBEDDING_DIMENSIONS


@pytest.mark.asyncio
@pytest.mark.parametrize("response", [SimpleNamespace(embeddings=[]), SimpleNamespace(embeddings=[SimpleNamespace(values=None)])])
async def test_embed_text_rejects_missing_embedding_values(mocker, response):
    mocker.patch.object(gemini_client, "_get_client", return_value=_client(response))

    with pytest.raises(AIIntegrationError, match="no embedding"):
        await gemini_client.embed_text("Python")
