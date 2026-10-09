# Frontend
---

React 19 + TypeScript SPA built with Vite, Tailwind v4 + shadcn/ui (Radix primitives), Zustand, and TanStack Query.

This is the frontend for ManifestCV. See the repository root [`README.md`](../README.md) for setup and [`docs/app/architecture/frontend.md`](../docs/app/architecture/frontend.md) for ManifestCV's routes, module layout, and state-management conventions. Mystic Auth's inherited frontend behavior is documented separately under `docs/mystic_auth/`.

---

## 1. Source layout
---

| Path | Purpose |
|---|---|
| `frontend/src/mystic_auth/` | Template-owned frontend: auth pages, PBAC gates, dashboard, users, policies, audit logs, settings, layout, UI primitives, translations, theme, API clients, and stores. |
| `frontend/src/app/` | Downstream application extension surface: app routes, app SDK exports, legal/status/landing pages, app theme overrides, and project-owned frontend code. |
| `tests/frontend/mystic_auth/` | Template-owned frontend unit, integration, and browser E2E coverage. |
| `tests/frontend/app/` | Downstream app test area. |

---

## 2. Scripts
---

> Commands below assume you're in `frontend/` (`cd frontend` from the repository root).

```bash
npm run dev         # Vite dev server
npm run build        # tsc -b && vite build (production build)
npm run typecheck    # tsc --noEmit across app/node/test tsconfigs
npm run lint         # eslint over frontend/ and tests/frontend/
npm run test          # vitest run (no coverage)
npm run test:coverage # vitest run --coverage (thresholds enforced)
npm run test:browser  # Playwright browser matrix against the running stack
```

See [`docs/app/testing/overview.md`](../docs/app/testing/overview.md) for what each suite covers.

Vitest coverage thresholds are defined in `frontend/vitest.config.ts` and are
enforced by `npm run test:coverage`. Browser route and layout behavior is
covered by Playwright; see the [app testing overview](../docs/app/testing/overview.md)
for the suite split and the [CI/CD overview](../docs/app/cicd/overview.md) for
the full-stack browser job.

Browser-only operations such as file downloads are mocked at the jsdom
boundary in Vitest. Their request, filename, and cleanup behavior remain
covered without asking jsdom to navigate to a new document.

---

## 3. Documentation
---

1. [ManifestCV Frontend Architecture](../docs/app/architecture/frontend.md)
2. [ManifestCV App Documentation](../docs/app/README.md)
3. [Mystic Auth Frontend Architecture](../docs/mystic_auth/architecture/frontend.md)
4. [Mystic Auth Frontend Customization](../docs/mystic_auth/template-usage/frontend-customization.md)
5. [Mystic Auth Translations Overview](../docs/mystic_auth/translations/overview/README.md)
6. [Mystic Auth Appearance](../docs/mystic_auth/appearance/overview.md)
7. [Mystic Auth Testing Overview](../docs/mystic_auth/testing/overview.md)

The `/` landing page is app-owned product UI. Its copy, layout, and translation
namespace live under `src/app/`, while authentication, shared controls, and the
signed-in redirect are consumed through `src/app/sdk.ts`. When changing it,
keep the `#main-content` skip-link target and run the browser accessibility
check; do not restore the template's sample “Auth & Authorization” headline as
a test workaround.

---
