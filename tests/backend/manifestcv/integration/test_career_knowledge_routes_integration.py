# tests/backend/manifestcv/integration/test_career_knowledge_routes_integration.py
#
# End-to-end coverage for /career-knowledge/* against the real ASGI app,
# real PostgreSQL, and real Redis (see tests/backend/conftest.py). The
# AI (Gemini) and vector-retrieval (Qdrant) calls are mocked at the route
# module's import site — this suite verifies HTTP/ownership/DB behavior,
# not Gemini/Qdrant themselves (there's no real API key in test envs, and
# AI/retrieval correctness belongs to ai_integration/retrieval's own tests).
import uuid

import pytest

from mystic_auth.auth.verify_account.account_verification_service import account_verification_service
from mystic_auth.authorization.policies.default_policies import SELF_SERVICE_POLICY_NAME
from mystic_auth.authorization.repositories.policy_repository import policy_repository
from mystic_auth.database.connection import database
from mystic_auth.redis.client import redis_client
from mystic_auth.user_crud.user_crud_collector import user_crud

ROUTES_MODULE = "backend.app.api.career_knowledge_routes.career_knowledge_routes"
PASSWORD = "StrongPass123!"


def _unique_email(prefix: str = "mcv-ck") -> str:
    return f"{prefix}-{uuid.uuid4().hex}@example.com"


async def _create_verified_user(client, created_emails, email: str):
    signup_resp = await client.post(
        "/auth/signup", json={"name": "Test User", "email": email, "password": PASSWORD}
    )
    assert signup_resp.status_code == 200
    created_emails.append(email)

    token = await account_verification_service.create_verification_token(email)
    await redis_client.set(f"verify:{token}", "1", ex=600)
    verify_resp = await client.post("/auth/verify-account", json={"token": token})
    assert verify_resp.status_code == 200

    async with database.async_session() as session:
        user = await user_crud.get_by_email(email, session)
        policy = await policy_repository.get_by_name(SELF_SERVICE_POLICY_NAME, session)
        await policy_repository.assign_policy_to_user(
            user_id=user.id, policy_id=policy.id, db=session, assigned_by="test"
        )

    login_resp = await client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert login_resp.status_code == 200


@pytest.fixture(autouse=True)
def _mock_ai_and_retrieval(mocker):
    from unittest.mock import AsyncMock

    return {
        "structure": mocker.patch(
            f"{ROUTES_MODULE}.structure_knowledge_base", new_callable=AsyncMock, return_value="# Structured\n\nMarkdown."
        ),
        "index": mocker.patch(f"{ROUTES_MODULE}.index_knowledge_base", new_callable=AsyncMock),
        "delete_index": mocker.patch(f"{ROUTES_MODULE}.delete_knowledge_base", new_callable=AsyncMock),
        "search": mocker.patch(f"{ROUTES_MODULE}.search_knowledge_base", new_callable=AsyncMock, return_value=[]),
    }


@pytest.mark.asyncio
async def test_career_knowledge_requires_authentication(client):
    response = await client.get("/career-knowledge/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_get_update_delete_flow(client, created_emails, _mock_ai_and_retrieval):
    email = _unique_email()
    await _create_verified_user(client, created_emails, email)

    create_resp = await client.post("/career-knowledge/", json={"raw_input": "Raw resume text dump."})
    assert create_resp.status_code == 201
    body = create_resp.json()
    assert body["raw_input"] == "Raw resume text dump."
    assert body["content"] == "# Structured\n\nMarkdown."
    _mock_ai_and_retrieval["structure"].assert_awaited_once_with("Raw resume text dump.")
    _mock_ai_and_retrieval["index"].assert_awaited_once()

    # Only one knowledge base per user — a second create is a conflict.
    second_create_resp = await client.post("/career-knowledge/", json={"raw_input": "More text."})
    assert second_create_resp.status_code == 409

    get_resp = await client.get("/career-knowledge/")
    assert get_resp.status_code == 200
    assert get_resp.json()["content"] == "# Structured\n\nMarkdown."

    # A bare content edit (no raw_input) skips AI structuring entirely.
    _mock_ai_and_retrieval["structure"].reset_mock()
    direct_edit_resp = await client.put("/career-knowledge/", json={"content": "# Hand-edited"})
    assert direct_edit_resp.status_code == 200
    assert direct_edit_resp.json()["content"] == "# Hand-edited"
    _mock_ai_and_retrieval["structure"].assert_not_awaited()

    # A fresh raw_input re-dump regenerates content via AI from scratch.
    re_dump_resp = await client.put("/career-knowledge/", json={"raw_input": "New dump."})
    assert re_dump_resp.status_code == 200
    assert re_dump_resp.json()["content"] == "# Structured\n\nMarkdown."
    _mock_ai_and_retrieval["structure"].assert_awaited_once_with("New dump.")

    delete_resp = await client.delete("/career-knowledge/")
    assert delete_resp.status_code == 200
    _mock_ai_and_retrieval["delete_index"].assert_awaited_once()

    get_after_delete = await client.get("/career-knowledge/")
    assert get_after_delete.status_code == 404


@pytest.mark.asyncio
async def test_ai_integration_failure_surfaces_as_502(client, created_emails, _mock_ai_and_retrieval):
    from backend.app.ai_integration.exceptions import AIIntegrationError

    email = _unique_email()
    await _create_verified_user(client, created_emails, email)

    _mock_ai_and_retrieval["structure"].side_effect = AIIntegrationError("Gemini unavailable")

    response = await client.post("/career-knowledge/", json={"raw_input": "Raw text."})
    assert response.status_code == 502


@pytest.mark.asyncio
async def test_search_is_scoped_to_the_caller_and_forwards_query_params(client, created_emails, _mock_ai_and_retrieval):
    email = _unique_email()
    await _create_verified_user(client, created_emails, email)

    async with database.async_session() as session:
        user = await user_crud.get_by_email(email, session)

    response = await client.get("/career-knowledge/search", params={"query": "python backend", "top_k": 3})
    assert response.status_code == 200
    assert response.json() == []
    _mock_ai_and_retrieval["search"].assert_awaited_once_with(user.id, "python backend", 3)


@pytest.mark.asyncio
async def test_search_retrieval_failure_surfaces_as_502(client, created_emails, _mock_ai_and_retrieval):
    from backend.app.retrieval.exceptions import RetrievalError

    email = _unique_email()
    await _create_verified_user(client, created_emails, email)

    _mock_ai_and_retrieval["search"].side_effect = RetrievalError("Qdrant unreachable")

    response = await client.get("/career-knowledge/search", params={"query": "python backend"})
    assert response.status_code == 502


@pytest.mark.asyncio
async def test_indexing_failure_is_best_effort_and_does_not_fail_create_update_delete(
    client, created_emails, _mock_ai_and_retrieval
):
    """
    index_knowledge_base/delete_knowledge_base failures must never fail the
    request that triggers them — the Postgres write is the source of truth
    and has already committed by the time indexing runs; a Qdrant outage
    should degrade to "search is stale" (see career_knowledge_routes.py's
    _reindex_best_effort/_delete_index_best_effort), never a 500 on a save
    that actually succeeded.
    """
    from backend.app.retrieval.exceptions import RetrievalError

    email = _unique_email()
    await _create_verified_user(client, created_emails, email)

    _mock_ai_and_retrieval["index"].side_effect = RetrievalError("Qdrant unreachable")

    create_resp = await client.post("/career-knowledge/", json={"raw_input": "Raw resume text dump."})
    assert create_resp.status_code == 201
    assert create_resp.json()["content"] == "# Structured\n\nMarkdown."

    update_resp = await client.put("/career-knowledge/", json={"content": "# Hand-edited"})
    assert update_resp.status_code == 200
    assert update_resp.json()["content"] == "# Hand-edited"

    _mock_ai_and_retrieval["delete_index"].side_effect = RetrievalError("Qdrant unreachable")

    delete_resp = await client.delete("/career-knowledge/")
    assert delete_resp.status_code == 200

    get_after_delete = await client.get("/career-knowledge/")
    assert get_after_delete.status_code == 404
