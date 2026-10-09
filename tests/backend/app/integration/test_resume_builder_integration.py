import uuid

import pytest

from backend.app.sdk import valkey_client
from backend.mystic_auth.auth.verify_account.account_verification_service import (
    account_verification_service,
)
from backend.mystic_auth.authorization.policies.default_policies import (
    SELF_SERVICE_POLICY_NAME,
)
from backend.mystic_auth.authorization.repositories.policy_repository import (
    policy_repository,
)
from backend.mystic_auth.database.connection import database
from backend.mystic_auth.user.user_crud_collector import user_crud

PASSWORD = "StrongPass123!"


def _email(prefix: str = "builder") -> str:
    return f"{prefix}-{uuid.uuid4().hex}@example.com"


async def _login_user(client, created_emails, email: str) -> None:
    signup = await client.post(
        "/auth/signup", json={"name": "Builder User", "email": email, "password": PASSWORD}
    )
    assert signup.status_code == 200
    created_emails.append(email)
    token = await account_verification_service.create_verification_token(email)
    await valkey_client.set(f"verify:{token}", "1", ex=600)
    verified = await client.post("/auth/verify-account", json={"token": token})
    assert verified.status_code == 200
    async with database.async_session() as session:
        user = await user_crud.get_by_email(email, session)
        policy = await policy_repository.get_by_name(SELF_SERVICE_POLICY_NAME, session)
        await policy_repository.assign_policy_to_user(
            user_id=user.id, policy_id=policy.id, db=session, assigned_by="test"
        )
    login = await client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_builder_requires_authentication(client):
    assert (await client.get("/resume-workspaces")).status_code == 401
    assert (await client.get("/resume-workspaces/templates")).status_code == 200


@pytest.mark.asyncio
async def test_workspace_revision_preview_export_and_application_snapshot(client, created_emails):
    await _login_user(client, created_emails, _email())

    created = await client.post(
        "/resume-workspaces",
        json={
            "title": "Acme application",
            "job_description": "Senior backend engineer at Acme",
            "template_key": "classic_single_column",
        },
    )
    assert created.status_code == 201
    workspace = created.json()
    workspace_id = workspace["id"]
    revision_id = workspace["current_revision_id"]
    assert workspace["template_key"] == "classic_single_column"

    detail = await client.get(f"/resume-workspaces/{workspace_id}")
    assert detail.status_code == 200
    document = detail.json()["revision"]["document"]
    document["blocks"][0]["content"] = {"name": "Builder User", "headline": "Engineer"}
    saved = await client.put(
        f"/resume-workspaces/{workspace_id}/document",
        json={"document": document, "expected_revision_id": revision_id},
    )
    assert saved.status_code == 200
    assert saved.json()["revision_number"] == 2

    preview = await client.get(f"/resume-workspaces/{workspace_id}/preview")
    assert preview.status_code == 200
    assert preview.headers["content-type"].startswith("text/html")
    assert "Builder User" in preview.text
    assert "script" not in preview.text.lower()

    assert (await client.post(f"/resume-workspaces/{workspace_id}/approve")).status_code == 200
    export_job = await client.post(f"/resume-workspaces/{workspace_id}/export-job")
    assert export_job.status_code == 202
    export_job_id = export_job.json()["id"]
    export_status = await client.get(f"/resume-jobs/{export_job_id}")
    assert export_status.json()["status"] in {"queued", "running", "succeeded"}
    if export_status.json()["status"] != "succeeded":
        not_ready = await client.get(f"/resume-jobs/{export_job_id}/download")
        assert not_ready.status_code == 409
    export = await client.get(f"/resume-workspaces/{workspace_id}/export")
    assert export.status_code == 200
    assert export.headers["content-type"] == "application/pdf"
    assert export.content.startswith(b"%PDF-")

    application = await client.post(
        "/applications/",
        json={
            "workspace_id": workspace_id,
            "company_name": "Acme Corp",
            "role": "Senior Backend Engineer",
            "application_date": "2026-07-19",
            "status": "applied",
        },
    )
    assert application.status_code == 201
    body = application.json()
    assert body["resume_workspace_id"] == workspace_id
    assert body["resume_revision_id"] == saved.json()["id"]
    assert body["template_id_snapshot"] == "classic_single_column"
    assert body["role"] == "Senior Backend Engineer"
    assert body["document_snapshot"]

@pytest.mark.asyncio
async def test_workspace_ownership_and_approval_are_enforced(client, created_emails):
    owner = _email("owner")
    await _login_user(client, created_emails, owner)
    created = await client.post(
        "/resume-workspaces",
        json={"title": "Private", "job_description": "Private role"},
    )
    workspace_id = created.json()["id"]
    await client.post("/auth/logout")
    await _login_user(client, created_emails, _email("other"))
    assert (await client.get(f"/resume-workspaces/{workspace_id}")).status_code == 404
    assert (await client.post(f"/resume-workspaces/{workspace_id}/approve")).status_code == 404


@pytest.mark.asyncio
async def test_generation_job_is_queued(client, created_emails):
    await _login_user(client, created_emails, _email("job"))
    created = await client.post(
        "/resume-workspaces", json={"title": "Queued resume", "job_description": "Backend role"}
    )
    workspace_id = created.json()["id"]
    queued = await client.post(f"/resume-workspaces/{workspace_id}/generate-job")
    assert queued.status_code == 202
    job_id = queued.json()["id"]
    assert (await client.get(f"/resume-jobs/{job_id}")).json()["status"] == "queued"
