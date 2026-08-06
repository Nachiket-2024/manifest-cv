# Documentation

- **[`mystic_auth/`](mystic_auth/README.md)**: the template's own reference docs: architecture, authentication, authorization (PBAC), database, API reference, background workers, security, testing, Docker, CI/CD, deployment, and [how to use this repo as a template](mystic_auth/template-usage/overview.md). Upstream-owned, do not edit it directly. `scripts/upstream-sync/sync-upstream.sh` updates it for you.
- **[`app/`](app/README.md)**: ManifestCV's own product docs: architecture, product features, database additions, API reference, testing, Docker, CI/CD, deployment, and known issues/concerns.

This mirrors the code split: `backend/mystic_auth/` plus `backend/app/`, and
`frontend/src/mystic_auth/` plus `frontend/src/app/`.
