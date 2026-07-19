# tests/backend/manifestcv/integration/test_document_routes_integration.py
#
# End-to-end coverage for /resumes/{draft_id}/templates, .../finalize, and
# .../finalize/download against the real ASGI app, real PostgreSQL, and
# real Redis (see tests/backend/conftest.py). render_resume_pdf (the actual
# tectonic/LaTeX compilation) is mocked in most tests here — this suite
# verifies the approval gate, ownership, and persistence around it, not
# LaTeX compilation itself. The two `test_real_tectonic_*` tests at the
# bottom are the exception: they skip the mock entirely and exercise the
# real markdown_to_latex -> templates -> tectonic_compiler pipeline, so a
# regression in the LaTeX escaping or a template's preamble (neither of
# which the mocked tests above can catch) fails CI instead of only
# surfacing in production. Skipped automatically wherever the `tectonic`
# binary isn't on PATH (any host running tests outside
# docker/backend.Dockerfile, which is the only image tectonic is installed
# in — see docker/overview.md).
import shutil
import uuid

import pytest
from unittest.mock import AsyncMock

from backend.app.auth.verify_account.account_verification_service import account_verification_service
from backend.app.authorization.policies.default_policies import SELF_SERVICE_POLICY_NAME
from backend.app.authorization.repositories.policy_repository import policy_repository
from backend.app.database.connection import database
from backend.app.redis.client import redis_client
from backend.app.user_crud.user_crud_collector import user_crud
from backend.app.resume_crud.resume_repository import resume_repository

ROUTES_MODULE = "backend.app.api.document_routes.document_routes"
PASSWORD = "StrongPass123!"

_TECTONIC_AVAILABLE = shutil.which("tectonic") is not None
_skip_unless_tectonic = pytest.mark.skipif(
    not _TECTONIC_AVAILABLE, reason="tectonic binary not on PATH — only installed in docker/backend.Dockerfile"
)


def _unique_email(prefix: str = "mcv-doc") -> str:
    return f"{prefix}-{uuid.uuid4().hex}@example.com"


async def _create_verified_user(client, created_emails, email: str) -> int:
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


async def _seed_approved_draft(user_id: int) -> int:
    async with database.async_session() as session:
        draft = await resume_repository.create(user_id, "Some job", "# My approved resume", session)
        await resume_repository.update(draft, {"status": "approved"}, session)
        return draft.id


@pytest.fixture
def _mock_pdf_rendering(mocker):
    return mocker.patch(
        f"{ROUTES_MODULE}.render_resume_pdf",
        new_callable=AsyncMock,
        return_value=("\\documentclass{article}...", b"%PDF-1.4 fake pdf bytes"),
    )


@pytest.mark.asyncio
async def test_document_routes_require_authentication(client):
    response = await client.get("/resumes/1/templates")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_operations_are_gated_behind_approval(client, created_emails):
    email = _unique_email()
    user_id = await _create_verified_user(client, created_emails, email)

    async with database.async_session() as session:
        unapproved_draft = await resume_repository.create(user_id, "Some job", "# Draft content", session)

    templates_resp = await client.get(f"/resumes/{unapproved_draft.id}/templates")
    assert templates_resp.status_code == 400

    finalize_resp = await client.post(
        f"/resumes/{unapproved_draft.id}/finalize", json={"template_id": "classic"}
    )
    assert finalize_resp.status_code == 400


@pytest.mark.asyncio
async def test_list_templates_returns_static_catalog(client, created_emails):
    email = _unique_email()
    user_id = await _create_verified_user(client, created_emails, email)
    draft_id = await _seed_approved_draft(user_id)

    response = await client.get(f"/resumes/{draft_id}/templates")
    assert response.status_code == 200
    assert len(response.json()) > 0
    assert all("id" in t and "label" in t for t in response.json())


@pytest.mark.asyncio
async def test_preview_compiles_on_the_fly_without_persisting(client, created_emails, _mock_pdf_rendering):
    email = _unique_email()
    user_id = await _create_verified_user(client, created_emails, email)
    draft_id = await _seed_approved_draft(user_id)

    response = await client.get(f"/resumes/{draft_id}/templates/classic/preview")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == b"%PDF-1.4 fake pdf bytes"
    _mock_pdf_rendering.assert_awaited_once_with("# My approved resume", "classic")

    # Nothing was persisted — a preview is compile-and-return only.
    not_found_resp = await client.get(f"/resumes/{draft_id}/finalize")
    assert not_found_resp.status_code == 404

    # Unlike every other route on this API (X-Frame-Options: DENY), the
    # preview route is deliberately embedded by the frontend in an
    # <iframe>/<embed> (see frontend/src/api/document_api.ts). The frontend
    # and backend are different origins, so framing is allowed via CSP
    # frame-ancestors naming the real frontend origin — not "SAMEORIGIN"
    # (which would only permit framing by this response's own origin, i.e.
    # never the frontend) and X-Frame-Options is omitted entirely, since it
    # has no cross-browser way to name a specific non-same origin — see
    # security_headers_middleware.py.
    from backend.app.core.settings import settings

    assert "X-Frame-Options" not in response.headers
    assert response.headers["Content-Security-Policy"] == f"default-src 'none'; frame-ancestors {settings.FRONTEND_BASE_URL}"


@pytest.mark.asyncio
async def test_unknown_template_id_is_rejected(client, created_emails):
    email = _unique_email()
    user_id = await _create_verified_user(client, created_emails, email)
    draft_id = await _seed_approved_draft(user_id)

    response = await client.post(f"/resumes/{draft_id}/finalize", json={"template_id": "does-not-exist"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_finalize_persists_and_can_be_fetched_and_downloaded(client, created_emails, _mock_pdf_rendering):
    email = _unique_email()
    user_id = await _create_verified_user(client, created_emails, email)
    draft_id = await _seed_approved_draft(user_id)

    # Nothing finalized yet.
    not_found_resp = await client.get(f"/resumes/{draft_id}/finalize")
    assert not_found_resp.status_code == 404

    finalize_resp = await client.post(f"/resumes/{draft_id}/finalize", json={"template_id": "classic"})
    assert finalize_resp.status_code == 200
    assert finalize_resp.json()["template_id"] == "classic"
    _mock_pdf_rendering.assert_awaited_once_with("# My approved resume", "classic")

    get_resp = await client.get(f"/resumes/{draft_id}/finalize")
    assert get_resp.status_code == 200
    assert get_resp.json()["template_id"] == "classic"

    download_resp = await client.get(f"/resumes/{draft_id}/finalize/download")
    assert download_resp.status_code == 200
    # The download route (as opposed to the preview route above) is not
    # meant to be framed — it's a direct file download, so it keeps the
    # API-wide DENY default.
    assert download_resp.headers["X-Frame-Options"] == "DENY"
    assert download_resp.headers["content-type"] == "application/pdf"
    assert download_resp.content == b"%PDF-1.4 fake pdf bytes"

    # Re-finalizing with a different template overwrites, not accumulates.
    refinalize_resp = await client.post(f"/resumes/{draft_id}/finalize", json={"template_id": "modern"})
    assert refinalize_resp.status_code == 200
    second_get_resp = await client.get(f"/resumes/{draft_id}/finalize")
    assert second_get_resp.json()["template_id"] == "modern"


# Deliberately includes LaTeX-special characters (%, &, #, $, _, {, }) that
# a resume plausibly contains (compensation figures, C#, email addresses,
# LaTeX-reserved punctuation in job titles) — markdown_to_latex.py must
# escape these correctly or tectonic fails to compile outright, exactly the
# class of bug the mocked tests above can't catch.
_REAL_RESUME_MARKDOWN = """# Jane Doe

## Summary
Backend engineer with 5+ years building APIs in C# & Python. Increased
throughput by 40% at a previous role; salary expectations $120k-$150k.

## Skills
* REST APIs, GraphQL, gRPC
* PostgreSQL, Redis, Docker & Kubernetes
* jane.doe@example.com | github.com/janedoe

## Experience
### Senior Engineer — Acme_Corp (2021-2024)
* Led a team of 3; #1 performer two years running.
* Reduced p99 latency by ~30% (measured under 100% load).
"""


@pytest.mark.asyncio
@_skip_unless_tectonic
@pytest.mark.parametrize("template_id", ["classic", "modern"])
async def test_real_tectonic_finalize_produces_a_valid_pdf(client, created_emails, template_id):
    email = _unique_email()
    user_id = await _create_verified_user(client, created_emails, email)

    async with database.async_session() as session:
        draft = await resume_repository.create(user_id, "Some job", _REAL_RESUME_MARKDOWN, session)
        await resume_repository.update(draft, {"status": "approved"}, session)

    finalize_resp = await client.post(f"/resumes/{draft.id}/finalize", json={"template_id": template_id})

    assert finalize_resp.status_code == 200
    assert finalize_resp.json()["template_id"] == template_id

    download_resp = await client.get(f"/resumes/{draft.id}/finalize/download")
    assert download_resp.status_code == 200
    assert download_resp.headers["content-type"] == "application/pdf"
    # A real tectonic-compiled PDF, not the mock's fixed placeholder bytes —
    # %PDF is the format's own magic number; a substantial byte count rules
    # out an empty/truncated document.
    assert download_resp.content.startswith(b"%PDF")
    assert len(download_resp.content) > 1000


@pytest.mark.asyncio
@_skip_unless_tectonic
async def test_real_tectonic_preview_compiles_without_persisting(client, created_emails):
    email = _unique_email()
    user_id = await _create_verified_user(client, created_emails, email)

    async with database.async_session() as session:
        draft = await resume_repository.create(user_id, "Some job", _REAL_RESUME_MARKDOWN, session)
        await resume_repository.update(draft, {"status": "approved"}, session)

    preview_resp = await client.get(f"/resumes/{draft.id}/templates/classic/preview")

    assert preview_resp.status_code == 200
    assert preview_resp.headers["content-type"] == "application/pdf"
    assert preview_resp.content.startswith(b"%PDF")

    # Preview never persists, real compilation or not.
    not_found_resp = await client.get(f"/resumes/{draft.id}/finalize")
    assert not_found_resp.status_code == 404


@pytest.mark.asyncio
async def test_documents_are_isolated_per_user(client, created_emails):
    owner_email = _unique_email("owner")
    owner_id = await _create_verified_user(client, created_emails, owner_email)
    draft_id = await _seed_approved_draft(owner_id)

    await client.post("/auth/logout")
    other_email = _unique_email("other")
    await _create_verified_user(client, created_emails, other_email)

    other_resp = await client.get(f"/resumes/{draft_id}/templates")
    assert other_resp.status_code == 404
