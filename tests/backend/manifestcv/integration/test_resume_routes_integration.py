# tests/backend/manifestcv/integration/test_resume_routes_integration.py
#
# End-to-end coverage for /resumes/* against the real ASGI app, real
# PostgreSQL, and real Redis (see tests/backend/conftest.py). AI (Gemini)
# and retrieval (Qdrant) calls are mocked at the route module's import
# site — see test_career_knowledge_routes_integration.py's module docstring
# for why.
import uuid

import pytest
from unittest.mock import AsyncMock

from mystic_auth.auth.verify_account.account_verification_service import account_verification_service
from mystic_auth.authorization.policies.default_policies import SELF_SERVICE_POLICY_NAME
from mystic_auth.authorization.repositories.policy_repository import policy_repository
from mystic_auth.database.connection import database
from mystic_auth.redis.client import redis_client
from mystic_auth.user_crud.user_crud_collector import user_crud

ROUTES_MODULE = "backend.app.api.resume_routes.resume_routes"
PASSWORD = "StrongPass123!"


def _unique_email(prefix: str = "mcv-resume") -> str:
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
    return {
        "search": mocker.patch(
            f"{ROUTES_MODULE}.search_knowledge_base",
            new_callable=AsyncMock,
            return_value=[{"chunk": "Worked on backend systems.", "score": 0.9}],
        ),
        "generate": mocker.patch(
            f"{ROUTES_MODULE}.generate_resume", new_callable=AsyncMock, return_value="# Generated Resume"
        ),
        "refine": mocker.patch(
            f"{ROUTES_MODULE}.refine_resume", new_callable=AsyncMock, return_value="# Refined Resume"
        ),
    }


@pytest.mark.asyncio
async def test_resumes_require_authentication(client):
    response = await client.get("/resumes/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_resume_draft_rejects_empty_knowledge_base(client, created_emails, _mock_ai_and_retrieval):
    email = _unique_email()
    await _create_verified_user(client, created_emails, email)
    _mock_ai_and_retrieval["search"].return_value = []

    response = await client.post("/resumes/", json={"job_description": "Backend engineer at Acme"})
    assert response.status_code == 400
    _mock_ai_and_retrieval["generate"].assert_not_awaited()


@pytest.mark.asyncio
async def test_create_resume_draft_surfaces_retrieval_failure_as_502(client, created_emails, _mock_ai_and_retrieval):
    from backend.app.retrieval.exceptions import RetrievalError

    email = _unique_email()
    await _create_verified_user(client, created_emails, email)
    _mock_ai_and_retrieval["search"].side_effect = RetrievalError("Qdrant unreachable")

    response = await client.post("/resumes/", json={"job_description": "Backend engineer at Acme"})
    assert response.status_code == 502
    _mock_ai_and_retrieval["generate"].assert_not_awaited()


@pytest.mark.asyncio
async def test_full_draft_lifecycle(client, created_emails, _mock_ai_and_retrieval):
    email = _unique_email()
    await _create_verified_user(client, created_emails, email)

    create_resp = await client.post("/resumes/", json={"job_description": "Backend engineer at Acme"})
    assert create_resp.status_code == 201
    body = create_resp.json()
    assert body["resume_content"] == "# Generated Resume"
    assert body["status"] == "draft"
    draft_id = body["id"]
    _mock_ai_and_retrieval["generate"].assert_awaited_once_with(
        "Backend engineer at Acme", ["Worked on backend systems."]
    )

    list_resp = await client.get("/resumes/")
    assert list_resp.status_code == 200
    assert [d["id"] for d in list_resp.json()] == [draft_id]

    # Direct manual edit — no AI call.
    edit_resp = await client.put(f"/resumes/{draft_id}", json={"content": "# Hand-edited resume"})
    assert edit_resp.status_code == 200
    assert edit_resp.json()["resume_content"] == "# Hand-edited resume"
    _mock_ai_and_retrieval["refine"].assert_not_awaited()

    # refinement_prompt re-matches the knowledge base and calls refine_resume.
    refine_resp = await client.put(f"/resumes/{draft_id}", json={"refinement_prompt": "Make it more concise"})
    assert refine_resp.status_code == 200
    assert refine_resp.json()["resume_content"] == "# Refined Resume"
    _mock_ai_and_retrieval["refine"].assert_awaited_once()

    approve_resp = await client.post(f"/resumes/{draft_id}/approve")
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "approved"

    # Content is locked once approved.
    locked_edit_resp = await client.put(f"/resumes/{draft_id}", json={"content": "Should be rejected"})
    assert locked_edit_resp.status_code == 400

    delete_resp = await client.delete(f"/resumes/{draft_id}")
    assert delete_resp.status_code == 200

    get_after_delete = await client.get(f"/resumes/{draft_id}")
    assert get_after_delete.status_code == 404


@pytest.mark.asyncio
async def test_cannot_approve_draft_with_no_content(client, created_emails, _mock_ai_and_retrieval):
    email = _unique_email()
    await _create_verified_user(client, created_emails, email)
    _mock_ai_and_retrieval["generate"].return_value = None

    create_resp = await client.post("/resumes/", json={"job_description": "Backend engineer at Acme"})
    assert create_resp.status_code == 201
    draft_id = create_resp.json()["id"]

    approve_resp = await client.post(f"/resumes/{draft_id}/approve")
    assert approve_resp.status_code == 400


@pytest.mark.asyncio
async def test_drafts_are_isolated_per_user(client, created_emails, _mock_ai_and_retrieval):
    owner_email = _unique_email("owner")
    await _create_verified_user(client, created_emails, owner_email)
    create_resp = await client.post("/resumes/", json={"job_description": "Owner's job"})
    draft_id = create_resp.json()["id"]

    await client.post("/auth/logout")
    other_email = _unique_email("other")
    await _create_verified_user(client, created_emails, other_email)

    other_get_resp = await client.get(f"/resumes/{draft_id}")
    assert other_get_resp.status_code == 404

    other_list_resp = await client.get("/resumes/")
    assert other_list_resp.status_code == 200
    assert other_list_resp.json() == []


@pytest.mark.asyncio
async def test_list_drafts_is_paginated_newest_first(client, created_emails, _mock_ai_and_retrieval):
    email = _unique_email()
    await _create_verified_user(client, created_emails, email)

    draft_ids = []
    for job_description in ["Job A", "Job B", "Job C"]:
        create_resp = await client.post("/resumes/", json={"job_description": job_description})
        assert create_resp.status_code == 201
        draft_ids.append(create_resp.json()["id"])

    # Default order is newest first — draft_ids were created oldest to newest.
    default_resp = await client.get("/resumes/")
    assert [d["id"] for d in default_resp.json()] == list(reversed(draft_ids))

    page_1 = await client.get("/resumes/", params={"limit": 2, "offset": 0})
    assert [d["id"] for d in page_1.json()] == list(reversed(draft_ids))[:2]

    page_2 = await client.get("/resumes/", params={"limit": 2, "offset": 2})
    assert [d["id"] for d in page_2.json()] == list(reversed(draft_ids))[2:]

    out_of_range = await client.get("/resumes/", params={"limit": 2, "offset": 10})
    assert out_of_range.json() == []

    invalid_limit = await client.get("/resumes/", params={"limit": 0})
    assert invalid_limit.status_code == 422
