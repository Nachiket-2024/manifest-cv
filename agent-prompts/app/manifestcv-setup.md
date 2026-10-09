# Set up ManifestCV for local development

Set up this existing ManifestCV repository for local development. ManifestCV is
the product layer. Mystic Auth supplies the shared identity, session, and
authorization foundation.

## Ownership rules

Read these files before changing anything:

- `agent-prompts/mystic_auth/new-project-setup.md`
- `docs/app/auth/overview.md`
- `docs/mystic_auth/deployment/environment.md`
- `docs/mystic_auth/template-usage/ownership-split.md`

Do not edit or replace Mystic Auth-owned files while setting up the app:

- `backend/mystic_auth/`
- `frontend/src/mystic_auth/`
- `docs/mystic_auth/`
- `screenshots/mystic_auth/`
- `scripts/mystic_auth/`
- tracked `docker/mystic_auth/` files
- tracked `env/mystic_auth/*.example` files

ManifestCV-owned product changes belong under `backend/app/`,
`frontend/src/app/`, `docs/app/`, `screenshots/app/`, `agent-prompts/app/`,
`docker/app/`, and `env/app/`. Shared entry points may need to be extended in
place, but do not duplicate Mystic Auth internals in the app layer. Root-level
shared configuration such as `.gitignore`, `.dockerignore`, dependency
manifests, and `.github/workflows/ci.yml` may also need a ManifestCV-specific
addition; follow the Shared tier in
`docs/mystic_auth/template-usage/ownership-split.md` and extend those files in
place. Do not treat every file outside the app directories as Mystic Auth
owned.

## Environment setup

1. Check only whether these runtime files exist. Do not print or read their
   contents:

   - `env/mystic_auth/.env.dev`
   - `env/app/.env.dev`

2. If either runtime file is missing, follow the shared Mystic Auth setup
   prompt at `agent-prompts/mystic_auth/new-project-setup.md` for safe runtime
   generation. Do not paste secrets into the agent conversation.

3. Keep shared values such as `APP_NAME`, database names, URLs, credentials,
   and shared service configuration in the matching runtime file under
   `env/mystic_auth/`, as described by the environment documentation. Keep
   ManifestCV-only values in `env/app/`. Do not edit tracked example files to
   configure one machine.

4. Confirm the app examples exist for the same deployment modes as the Mystic
   Auth examples. Do not create a generic extra app env file.

## Start and verify the product

Use the development Compose pair:

```bash
docker compose \
  -f docker/mystic_auth/compose/docker-compose.dev.yml \
  -f docker/app/compose/docker-compose.dev.yml \
  --env-file env/mystic_auth/.env.dev \
  --env-file env/app/.env.dev \
  up -d --build
```

Wait for the services to become healthy, then verify:

- `http://localhost:5173` serves the ManifestCV frontend
- `http://localhost:8000/health/ready` reports an OK health status
- `http://localhost:8000/docs` serves the API documentation
- the database, Valkey, Qdrant, migration runner, backend, frontend, and
  Procrastinate worker are running as expected

Use the configured `*_HOST_PORT` values when runtime configuration changes the
defaults. Do not assume a port is available just because the default is shown.

## Product smoke check

After the stack is healthy, verify the current ManifestCV flow rather than
only the shared login screen:

1. Open the landing page.
2. Sign in using an existing local account, or follow the documented
   first-time system account procedure if the environment is empty.
3. Open Career Knowledge and confirm the page loads.
4. Open Resume Studio and confirm the workspace list and creation flow load.
5. Open Applications and confirm the page loads.

Do not create or document screenshots of Mystic Auth administration pages such
as permissions, policies, rate limits, or security audit screens in
`screenshots/app/`. Those belong under `screenshots/mystic_auth/`.

## Final checks

Run the smallest relevant checks after setup:

```bash
docker compose \
  -f docker/mystic_auth/compose/docker-compose.dev.yml \
  -f docker/app/compose/docker-compose.dev.yml \
  --env-file env/mystic_auth/.env.dev \
  --env-file env/app/.env.dev \
  config --quiet
```

If a setup check fails, report the service, command, and non-secret error
message. Never print runtime env contents, tokens, passwords, API keys, or
cookie values. For broader product checks, use `docs/app/testing/overview.md`.
