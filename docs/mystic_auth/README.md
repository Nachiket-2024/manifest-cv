# Documentation

Documentation for this full-stack template, organized by feature/domain to mirror the actual code layout (`backend/mystic_auth/<domain>/`, `frontend/src/mystic_auth/<domain>/`). If something here disagrees with the code, the code wins — file an issue or update the doc.

This is the template's own reference documentation — upstream's, not yours to edit. Your own project's docs go in [`docs/app/`](../app/README.md) instead, so they never conflict with a future `git merge upstream/main`. See [Using This Repository as a Template: the `app/` + `mystic_auth/` split](template-usage.md#the-app--mystic_auth-split) for the full reasoning.

## Architecture

- [System Overview](architecture/system-overview.md) — whole-stack component diagram, why the stack is split this way, request lifecycle
- [Backend Architecture](architecture/backend.md) — `backend/mystic_auth/` module layout, request pipeline, middleware
- [Frontend Architecture](architecture/frontend.md) — `frontend/src/mystic_auth/` module layout, state management, routing, theming

## Authentication

- [Authentication Overview](authentication/overview.md) — signup, verification, login, refresh/logout, password reset, JWT/cookie mechanics
- [OAuth2 / PKCE](authentication/oauth2-pkce.md) — Google OAuth2 login flow, PKCE code-challenge mechanics, CSRF state protection

## Authorization (PBAC)

- [Architecture Overview](authorization/architecture.md) — request flow, component responsibilities, integration points
- [Policy JSON Examples](authorization/policy-examples.md) — basic, conditioned, superuser, and self-service policies
- [Condition Schema Reference](authorization/condition-schema-reference.md) — every supported condition type, field-by-field
- [Adding New Permissions](authorization/adding-permissions.md) — extending the action vocabulary
- [Adding New Condition Handlers](authorization/adding-condition-handlers.md) — extending the condition framework
- [Writing and Testing Policies](authorization/writing-testing-policies.md) — policy lifecycle, local testing, unit test patterns
- [Operational Troubleshooting Guide](authorization/troubleshooting.md) — common issues, logging, Redis/DB debugging

## Database

- [Database Design](database/design.md) — schema, foreign keys, account lifecycle (soft delete/purge/reactivate)

## API

- [API Reference](api/reference.md) — route inventory grouped by domain, request/response shapes, auth requirements

## Background Workers

- [Taskiq Background Workers](background-workers/taskiq.md) — broker setup, task definitions, failure handling

## Security

- [Security Decisions](security/decisions.md) — the *why* behind non-obvious security choices, plus known accepted gaps
- [Security Hardening](security/hardening.md) — rate limiting, lockout, security headers, CORS, cookie flags, consolidated
- [SECURITY.md](../../SECURITY.md) — how to report a vulnerability privately (not via a public GitHub Issue)

## Error Monitoring

- [Error Monitoring](error-monitoring/overview.md) — enabled-by-default backend/frontend error reporting via the Sentry SDK protocol; self-hosted Bugsink quickstart, what gets reported, Sentry-hosted alternative

## Testing

- [Testing Overview](testing/overview.md) — backend pytest suites, frontend vitest suites, coverage state, how to run

## Docker

- [Docker Overview](docker/overview.md) — services, Dockerfiles, dev vs. prod compose, healthchecks, validation results

## CI/CD

- [CI/CD Overview](cicd/overview.md) — GitHub Actions workflow, jobs, gaps

## Deployment

- [Deployment Guide](deployment/guide.md) — dev vs. prod topology, environment variables, free/low-cost hosting options

## Concerns, Limitations & Technical Debt

- [Known Issues & Future Improvements](concerns/README.md) — tracked limitations, technical debt, deferred security/performance work

## Project Story

- [Project Story](project-story/README.md) — where this template came from and how it evolved, straight from the commit history

## Using This as a Template

- [Template Usage Guide](template-usage.md) — for anyone cloning this repo as a starting point for their own auth+PBAC project: quickstart, environment configuration, renaming the app, frontend/backend customization, OAuth/email setup, adding permissions and protecting routes, replacing the frontend, deployment

## Who this is for

Anyone adding a new protected endpoint, a new permission, a new condition type, or a new policy to this template; anyone integrating a new frontend feature against the API; anyone debugging why an authorization decision or a request came back the way it did; or anyone new to the codebase who needs the system-wide picture before touching auth, authorization, or infrastructure code.

## Source of truth

This documentation describes the code as it exists in `backend/mystic_auth/` and `frontend/src/mystic_auth/` at the time of writing. If something here disagrees with the code, the code wins.
