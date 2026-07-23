# tests/backend/manifestcv/integration/test_application_routes_integration.py
#
# End-to-end coverage for /applications/* against the real ASGI app, real
# PostgreSQL, and real Redis (see tests/backend/conftest.py). Unlike
# career_knowledge/resume routes, application_routes.py has no AI/Qdrant
# dependency, so it's exercised as a real HTTP flow rather than mocked —
# the one prerequisite (an existing finalized resume) is seeded directly
# via the repositories, the same way test_user_routes_integration.py seeds
# policy assignments directly rather than through the API.
import uuid

import pytest

from mystic_auth.auth.verify_account.account_verification_service import account_verification_service
from mystic_auth.authorization.policies.default_policies import SELF_SERVICE_POLICY_NAME
from mystic_auth.authorization.repositories.policy_repository import policy_repository
from mystic_auth.database.connection import database
from mystic_auth.redis.client import redis_client
from mystic_auth.user_crud.user_crud_collector import user_crud
from backend.app.resume_crud.resume_repository import resume_repository
from backend.app.resume_document_crud.resume_document_repository import resume_document_repository

PASSWORD = "StrongPass123!"


def _unique_email(prefix: str = "mcv") -> str:
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
    return user.id


async def _seed_finalized_resume(user_id: int) -> int:
    """Creates a resume draft + finalized document directly via the
    repositories — application creation requires one to exist, and
    finalization itself (document_routes.py) depends on tectonic/LaTeX
    compilation, which is out of scope for this route's own test."""
    async with database.async_session() as session:
        draft = await resume_repository.create(
            user_id, "Senior Engineer role at Acme Corp", "# My Resume\n\nContent.", session
        )
        await resume_document_repository.upsert(
            draft.id, "classic", "\\documentclass{article}...", b"%PDF-1.4 fake pdf bytes", session
        )
        return draft.id


@pytest.mark.asyncio
async def test_applications_require_authentication(client):
    response = await client.get("/applications/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_list_get_update_delete_application_flow(client, created_emails):
    email = _unique_email()
    user_id = await _create_verified_user(client, created_emails, email)
    draft_id = await _seed_finalized_resume(user_id)

    create_resp = await client.post(
        "/applications/",
        json={
            "resume_draft_id": draft_id,
            "company_name": "Acme Corp",
            "application_date": "2026-07-19",
            "status": "applied",
        },
    )
    assert create_resp.status_code == 201
    body = create_resp.json()
    assert body["company_name"] == "Acme Corp"
    assert body["resume_content_snapshot"] == "# My Resume\n\nContent."
    assert body["template_id_snapshot"] == "classic"
    application_id = body["id"]

    list_resp = await client.get("/applications/")
    assert list_resp.status_code == 200
    assert [a["id"] for a in list_resp.json()] == [application_id]
    # Summary schema deliberately excludes the resume content snapshot.
    assert "resume_content_snapshot" not in list_resp.json()[0]

    get_resp = await client.get(f"/applications/{application_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "applied"

    update_resp = await client.patch(f"/applications/{application_id}", json={"status": "interviewing"})
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "interviewing"
    # The resume snapshot itself is read-only once saved.
    assert update_resp.json()["resume_content_snapshot"] == "# My Resume\n\nContent."

    pdf_resp = await client.get(f"/applications/{application_id}/pdf")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert pdf_resp.content == b"%PDF-1.4 fake pdf bytes"

    delete_resp = await client.delete(f"/applications/{application_id}")
    assert delete_resp.status_code == 200

    get_after_delete = await client.get(f"/applications/{application_id}")
    assert get_after_delete.status_code == 404


@pytest.mark.asyncio
async def test_arbitrary_status_values_are_rejected(client, created_emails):
    """ApplicationCreate/Update.status is a fixed Literal (applied/
    interviewing/offered/rejected — see application_schema.py), matching the
    frontend's STATUS_OPTIONS. Free-text/arbitrary status strings must be
    rejected at the API boundary rather than silently persisted."""
    email = _unique_email()
    user_id = await _create_verified_user(client, created_emails, email)
    draft_id = await _seed_finalized_resume(user_id)

    create_resp = await client.post(
        "/applications/",
        json={
            "resume_draft_id": draft_id,
            "company_name": "Acme Corp",
            "application_date": "2026-07-19",
            "status": "not-a-real-status",
        },
    )
    assert create_resp.status_code == 422

    valid_create_resp = await client.post(
        "/applications/",
        json={
            "resume_draft_id": draft_id,
            "company_name": "Acme Corp",
            "application_date": "2026-07-19",
            "status": "applied",
        },
    )
    assert valid_create_resp.status_code == 201
    application_id = valid_create_resp.json()["id"]

    update_resp = await client.patch(
        f"/applications/{application_id}", json={"status": "not-a-real-status"}
    )
    assert update_resp.status_code == 422


@pytest.mark.asyncio
async def test_create_application_without_finalized_resume_is_rejected(client, created_emails):
    email = _unique_email()
    user_id = await _create_verified_user(client, created_emails, email)

    async with database.async_session() as session:
        draft = await resume_repository.create(user_id, "Some job", "# Draft", session)

    response = await client.post(
        "/applications/",
        json={
            "resume_draft_id": draft.id,
            "company_name": "Acme Corp",
            "application_date": "2026-07-19",
            "status": "applied",
        },
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_applications_are_isolated_per_user(client, created_emails):
    owner_email = _unique_email("owner")
    owner_id = await _create_verified_user(client, created_emails, owner_email)
    draft_id = await _seed_finalized_resume(owner_id)

    create_resp = await client.post(
        "/applications/",
        json={
            "resume_draft_id": draft_id,
            "company_name": "Owner's Company",
            "application_date": "2026-07-19",
            "status": "applied",
        },
    )
    assert create_resp.status_code == 201
    application_id = create_resp.json()["id"]

    # Log out the owner, then log in as a second, unrelated user.
    await client.post("/auth/logout")
    other_email = _unique_email("other")
    await _create_verified_user(client, created_emails, other_email)

    # Same _current_user_id -> user_id-scoped lookup as every other route:
    # a caller-supplied application_id belonging to a different user must
    # 404, not leak the other user's data or bypass ownership as a 403 would
    # incorrectly imply the row exists.
    other_get_resp = await client.get(f"/applications/{application_id}")
    assert other_get_resp.status_code == 404

    other_list_resp = await client.get("/applications/")
    assert other_list_resp.status_code == 200
    assert other_list_resp.json() == []


@pytest.mark.asyncio
async def test_list_applications_is_paginated_newest_first(client, created_emails):
    email = _unique_email()
    user_id = await _create_verified_user(client, created_emails, email)

    application_ids = []
    for i, company in enumerate(["Company A", "Company B", "Company C"]):
        draft_id = await _seed_finalized_resume(user_id)
        create_resp = await client.post(
            "/applications/",
            json={
                "resume_draft_id": draft_id,
                "company_name": company,
                "application_date": f"2026-07-{19 + i}",
                "status": "applied",
            },
        )
        assert create_resp.status_code == 201
        application_ids.append(create_resp.json()["id"])

    # Default order is newest first — application_ids were created oldest to newest.
    default_resp = await client.get("/applications/")
    assert [a["id"] for a in default_resp.json()] == list(reversed(application_ids))

    page_1 = await client.get("/applications/", params={"limit": 2, "offset": 0})
    assert [a["id"] for a in page_1.json()] == list(reversed(application_ids))[:2]

    page_2 = await client.get("/applications/", params={"limit": 2, "offset": 2})
    assert [a["id"] for a in page_2.json()] == list(reversed(application_ids))[2:]

    out_of_range = await client.get("/applications/", params={"limit": 2, "offset": 10})
    assert out_of_range.json() == []

    invalid_limit = await client.get("/applications/", params={"limit": 0})
    assert invalid_limit.status_code == 422
