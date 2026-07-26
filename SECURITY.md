# Security Policy

## Supported versions

There is one line of development, `main` — security fixes land there, no separate release branches to track.

## Reporting a vulnerability

**Please do not open a public GitHub Issue for a security vulnerability.** A public issue discloses the problem (and often enough detail to exploit it) before a fix exists.

Instead, report it privately via [GitHub's private vulnerability reporting](https://github.com/Nachiket-2024/manifest-cv/security/advisories/new) (Security tab → "Report a vulnerability"). Include:

- What the vulnerability is and where it lives (file/route/component).
- Steps to reproduce, or a proof-of-concept if you have one.
- The impact as you understand it (what an attacker could actually do with it).

You should get an acknowledgment within a few days. This is a personal project maintained on a best-effort basis, not a funded security team with a formal SLA — please be patient, and thank you for reporting responsibly rather than disclosing publicly first.

## Scope

Both layers of this app are in scope:

- **Identity/authorization**, inherited from [mystic-auth](https://github.com/Nachiket-2024/mystic-auth) — authentication (JWT/cookie handling, password hashing, rate limiting/lockout, OAuth2/PKCE), authorization (PBAC policy evaluation), and audit logging. See [Security Hardening](docs/mystic_auth/security/hardening.md) and [Security Decisions](docs/mystic_auth/security/decisions.md) for what's already been deliberately considered — a report that turns out to already be covered there (with reasoning for why the current behavior is intentional) will get a pointer to that doc rather than a fix, unless the report identifies a flaw in the reasoning itself. Since `mystic_auth/` is vendored in unmodified (see [Auth & Authorization](docs/app/auth/overview.md)), a vulnerability found there is also worth reporting upstream at [mystic-auth's own security policy](https://github.com/Nachiket-2024/mystic-auth/security/advisories/new) so every project built on the template gets the fix, not just this one.
- **ManifestCV's own product code** — career knowledge, resume generation/refinement, document (PDF) generation, application tracking, and the Gemini/Qdrant integration behind them (`backend/app/`, `frontend/src/app/`).

**Out of scope**: vulnerabilities in third-party dependencies (report those upstream, to the dependency's own maintainers — this repo scans for known dependency CVEs on every push/PR via `pip-audit`/`npm audit` in CI, see [CI/CD Overview](docs/app/cicd/overview.md)), and anything specific to how *you've* deployed or customized your own copy of this app (a misconfigured reverse proxy, a `SECRET_KEY`/`GEMINI_API_KEY` committed to your own fork, etc.).

## Known, already-tracked gaps

Not every limitation is a vulnerability to report — some are deliberate, documented scope boundaries. Check [Known Issues, Limitations & Technical Debt](docs/app/concerns/README.md) (ManifestCV's own) and [mystic-auth's own list](docs/mystic_auth/concerns/README.md) first; between the two, that's the running list of what's already known and why it's not (yet, or ever) fixed.
