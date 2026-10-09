# Contributing
---

This file is for anyone opening a pull request against **this repository itself**
(fixing a bug, adding a feature, improving the template's own code or docs). If
you started your own project from this template and want to customize it, or
pull in future template updates, see
[Using This Repository as a Template](docs/mystic_auth/template-usage/overview.md)
instead: that's a different audience with a different workflow.

---

## Before you start

Check [Known Issues, Limitations & Technical Debt](docs/mystic_auth/concerns/README.md)
and [existing issues](https://github.com/Nachiket-2024/mystic-auth/issues) first.
For anything beyond a small fix, open an issue describing what you want to
change before writing code, so the approach can be discussed before you've
sunk time into an implementation that might go a different direction.

**Found a security vulnerability?** Don't open a public issue or PR. See
[SECURITY.md](SECURITY.md) for private reporting.

---

## Local setup

Same as any other contributor: `./scripts/mystic_auth/env-tools/quickstart/quickstart.sh`
from a fresh clone. See the root [README's Quickstart](README.md#quickstart-docker)
or [Template Usage: Quickstart](docs/mystic_auth/template-usage/quickstart.md) for
the full walkthrough.

---

## Making a change

- **Follow the existing ownership split.** `backend/mystic_auth/`, `frontend/src/mystic_auth/`,
  `docs/mystic_auth/`, `scripts/mystic_auth/`, `docker/mystic_auth/`, and `env/mystic_auth/`
  are this template's own implementation, the actual surface a PR here touches.
  The parallel `app/` folders exist for template *consumers'* own code and stay
  empty in this repo; a PR shouldn't add anything there. See
  [The `app/` + `mystic_auth/` Split](docs/mystic_auth/template-usage/ownership-split.md)
  for the full reasoning.
- **Match the existing code style**, don't introduce a new one for just your
  change. Comments explain *why*, not *what* (see
  [Documentation Style](docs/mystic_auth/documentation-style.md) for the same
  rule applied to docs).
- **Update docs in the same PR as the code**, not as a follow-up. A behavior
  change with no doc update is treated as incomplete.
- **Add or update tests for what you changed.** See
  [Testing Overview](docs/mystic_auth/testing/overview.md) for how backend
  (pytest) and frontend (Vitest) suites are organized, and
  [Browser E2E Tests](docs/mystic_auth/testing/frontend-e2e.md) for Playwright.

---

## Before opening a PR

Run the same checks CI runs, so you're not waiting on CI to find a problem you
could catch locally. See [CI/CD Overview: Local equivalents](docs/mystic_auth/cicd/overview.md#local-equivalents)
for the exact commands (ruff/mypy/bandit, pytest, npm typecheck/lint/test,
Docker image builds). At minimum:

```bash
# Backend
cd backend && ruff check app mystic_auth alembic ../tests/backend && mypy app mystic_auth
python -m pytest tests/backend/app tests/backend/mystic_auth/unit -q

# Frontend
cd frontend && npm run typecheck && npm run lint && npm run test:coverage
```

A PR that fails CI on something the local checks above would have caught gets
sent back before review, not reviewed with known-red checks.

---

## Pull request

- Keep the PR focused: one fix or one feature, not an unrelated bundle.
- Describe *why*, not just *what* changed, in the PR description; the diff
  already shows *what*.
- Reference the issue it closes, if any.

---

See [Project Story](docs/mystic_auth/project-story/README.md) if you're curious how
this template got to its current shape, and [License](LICENSE) for the terms
your contribution is made under (MIT, same as the rest of the repo).

---
