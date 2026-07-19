# Frontend Architecture

## Purpose

React 19 + TypeScript SPA (`frontend/src/`), built with Vite, styled with Chakra UI v3. Feature-organized to mirror the backend's domain split, with a PBAC-aware UI layer that mirrors the backend's permission vocabulary. As with the backend, the identity/authorization UI is vendored from [mystic-auth](https://github.com/Nachiket-2024/mystic-auth); ManifestCV's own domains (`career_knowledge/`, `resumes/`, `applications/`) are added on top and never import from `auth/`, `authorization/`, or `store/authStore` directly — see [Auth & Authorization](../auth/overview.md).

## Module layout

### Inherited from mystic-auth

| Module | Purpose |
|---|---|
| `auth/` | Login, signup, logout, logout-all, OAuth2, password reset (request/confirm), account verification, current-user session query — each sub-feature is its own folder (Page/Form/mutation-hook/types) |
| `authorization/` | `permissions.ts` — frontend mirror of the backend `Permission` enum |
| `audit_log/` | `AuditLogPage.tsx` — the caller's own PBAC audit trail, plus an "all users" tab for privileged callers |
| `dashboard/` | Landing page after login |
| `policies/` | Admin CRUD UI for PBAC policies |
| `profile/` | Self-service profile view/update |
| `users_admin/` | Admin user management (list, mutate, assign policies) |
| `services/` | `authorizationService.ts` — batch permission-check calls, policy/audit-log fetches |
| `components/` | Shared UI: `layout/` (AppLayout, Navbar, Sidebar, ThemeToggle), `ui/` (DataTable, ConfirmDialog, FormAlert, PasswordRulesChecklist, toaster, LoadingState), plus the PBAC gates `Authorized`, `IfCan`, `ProtectedRoute` — ManifestCV's own pages reuse these `ui/` primitives directly |
| `hooks/` | `useAuthorization`/`useCan`, `usePasswordPolicy`, `useUnsavedChangesWarning` — the latter is also used by ManifestCV's editor pages |
| `store/` | Zustand: `authStore.ts` (session/profile/permissions), `themeStore.ts`; plus `queryClient.ts` (shared TanStack Query client, also used by ManifestCV's own query hooks) |
| `theme/` | `system.ts` — Chakra UI v3 design tokens |

### ManifestCV's own domains

| Module | Purpose |
|---|---|
| `career_knowledge/` | `CareerKnowledgePage.tsx` + query/mutation hooks — the caller's own knowledge base — see [Career Knowledge](../career-knowledge/overview.md) |
| `resumes/` | `ResumeDraftsPage.tsx`, `ResumeEditorPage.tsx` + query/mutation hooks — resume drafts and template finalization — see [Resumes](../resumes/overview.md) and [Document Generation](../document-generation/overview.md) |
| `applications/` | `ApplicationsPage.tsx` + query/mutation hooks — tracked applications — see [Applications](../applications/overview.md) |
| `api/application_api.ts`, `api/career_knowledge_api.ts`, `api/document_api.ts`, `api/resume_api.ts` | Axios-based typed call functions for the four ManifestCV route groups, alongside mystic-auth's own `api/*.ts` files |
| `core/settings.ts` | App-wide settings (`APP_NAME`, `VITE_API_BASE_URL`) — inherited from mystic-auth, unmodified |

## State management

- **Zustand** for client state — `authStore` (`isAuthenticated`, `name`, `email`, `role`, `permissions`, `hasPassword`) and `themeStore` (light/dark). No Redux.
- **TanStack Query** for all server state/caching, via one shared `QueryClient` (`store/queryClient.ts`).
- `authStore.isAuthenticated` starts as `null` ("not checked yet") — `App.tsx` blocks rendering the router behind a loading screen until `useAuthSession()` resolves it to `true`/`false`, avoiding a flash of unauthenticated content.

## API layer

`api/axiosInstance.ts` — a single Axios instance, `withCredentials: true` (cookie-based session; the JWT itself is never stored in JS-accessible state), base URL from `VITE_API_BASE_URL`. Per-domain typed call functions live in `api/*.ts` (`auth_api`, `users_api`, `policies_api`, `audit_api`, plus ManifestCV's own `application_api`, `career_knowledge_api`, `document_api`, `resume_api`); `api/apiError.ts` shapes error responses uniformly.

`api/setupAuthInterceptor.ts` implements silent-refresh-on-401: a single in-flight refresh call is shared across concurrently-failing requests (no thundering herd of refresh calls), and login/signup/refresh/logout/reset/verify/oauth2 endpoints are excluded from the retry-after-refresh logic to avoid infinite loops. On an unrecoverable 401, it marks `authStore` unauthenticated and clears the cached `GET /auth/me` query. It does not handle `403` — permission failures are left entirely to route/component-level guards (`ProtectedRoute`, `Authorized`, `IfCan`).

## Routing

`react-router-dom` v7, `BrowserRouter`, defined in `App.tsx`. Only `LoginPage` is eager-loaded (the most common unauthenticated entry point); every other route is `React.lazy`-split.

| Route | Access | Notes |
|---|---|---|
| `/`, `/dashboard` | authenticated | `DashboardPage` |
| `/users` | `USERS_LIST_ALL` | Admin user management |
| `/policies` | `POLICIES_READ` | PBAC policy admin |
| `/audit-log` | authenticated (self-service) | "All users" tab gated separately inside the page |
| `/profile` | authenticated | |
| `/career-knowledge` | authenticated (self-service) | ManifestCV — no permission required, ownership is server-side |
| `/resumes`, `/resumes/:draftId` | authenticated (self-service) | ManifestCV — drafts list and editor |
| `/applications` | authenticated (self-service) | ManifestCV — tracked applications |
| `/login`, `/signup`, `/verify-account`, `/password-reset-request`, `/reset-password` | public | |
| `/not-authorized` | public | 403 landing — where `ProtectedRoute` sends an authenticated-but-unauthorized user |
| `*` | public | 404 |

All protected routes are wrapped in `ProtectedRoute` (redirects unauthenticated → `/login`, unauthorized → `/not-authorized`) and `AppLayout` (sidebar/top-bar shell), so the shell only renders once access is actually confirmed.

## Authorization on the frontend (PBAC-aware UI)

- `authorization/permissions.ts` mirrors the backend's `Permission` enum as string constants, so route/component gates reference `PERMISSIONS.USERS_LIST_ALL` rather than a hand-typed string.
- `hooks/useAuthorization.ts` reads `authStore.permissions` and exposes `can(action)`, failing closed (`false`) when unauthenticated or still loading. This is a **client-side UX convenience only** — the backend independently enforces every action via `require_authorization`; a hidden button is not a security boundary.
- `components/ProtectedRoute.tsx`, `Authorized.tsx`, `IfCan.tsx` — route-level and in-page conditional gates built on `useAuthorization`.
- `services/authorizationService.ts` layers real per-resource/conditional checks (`POST /authorization/batch-check`) on top of the cached flat permission list for cases that need it.
- `role` is explicitly treated as metadata only on the frontend too — never used in a gating decision, mirroring the backend's own design.
- ManifestCV's own routes (`/career-knowledge`, `/resumes`, `/applications`) deliberately carry no `permission` prop — they're self-service, ownership-scoped resources, not PBAC-gated ones. See [Auth & Authorization](../auth/overview.md).

## Theming

Chakra UI v3 (`@chakra-ui/react` + Emotion). `theme/system.ts` defines the design tokens; `themeStore.ts` + `components/layout/ThemeToggle.tsx` handle light/dark switching, independent of the OS-level `prefers-color-scheme`.

## Build & bundling

`vite.config.ts` splits the production build into two top-level chunks via `build.rollupOptions.output.manualChunks`: everything under `node_modules` goes into a `vendor` chunk, and the app's own `src/` code (App shell + eagerly-loaded `LoginPage`) stays in the entry chunk.

- **Why**: without the split, every third-party dependency (`react-dom`, `@chakra-ui/react`, `axios`, `react-router-dom`, `@tanstack/react-query`) was bundled together with app code into one entry chunk. Since Vite content-hashes chunk filenames, any one-line app change busted the cache for the *entire* chunk — including ~740 kB of vendor code that hadn't actually changed. Splitting vendor into its own chunk means a deploy that only touches app code now only invalidates a ~20 kB (~7 kB gzip) chunk; the ~780 kB (~233 kB gzip) vendor chunk keeps its hash — and browser cache — across deploys that don't bump a dependency.
- **The `vendor` chunk still trips Vite's "chunk larger than 500 kB" build warning, and that's expected, not a regression to fix.** The bulk of it is Chakra UI v3's `defaultConfig` (imported by `theme/system.ts`, required at the app root by `ChakraProvider`): it's one object bundling style recipes for *every* built-in Chakra component, including several this app never renders (Menu, Combobox, TreeView, TagsInput, NumberInput, ColorPicker) — Rollup can tree-shake unused *modules* but not unused *properties* of an object that's genuinely referenced, so their `@zag-js/*` machine code (~150 kB+ unminified) comes along regardless. There's no supported way to hand-pick a subset of Chakra's default recipes without forking the theme system, so this is treated as a justified, inherent cost of the library choice rather than something to chase — `build.chunkSizeWarningLimit` is deliberately left untouched so the warning stays visible instead of being silenced.
- Route-level code splitting is separate and already in place — see [Routing](#routing) above: every route except `LoginPage` is `React.lazy`-loaded, so route chunks only ever contain that page's own code plus the Chakra sub-components it specifically imports.

## Configuration requirements

`frontend/.env.example` — `VITE_API_BASE_URL` (the backend's base URL) and `VITE_APP_NAME` (the product name shown in the UI — navbar, auth pages, document title via `index.html`'s `%VITE_APP_NAME%` substitution). Both are Vite build-time env vars, read through `core/settings.ts`. Support email shown in emails is backend-driven (`SUPPORT_EMAIL`) and only ever appears in server-rendered email templates, not in the frontend build.

## Edge cases / error handling

- A 401 mid-session (expired access token) triggers one silent refresh-and-retry; a second failure marks the session invalid and, per route, redirects to `/login`.
- A 403 (authorization denial) is a normal API response the calling component/page is responsible for handling — typically a toast or an inline `FormAlert`, not a global redirect (except at the route level via `ProtectedRoute`).

## Testing coverage

Tests live in `tests/frontend/` (outside `src/`), not co-located — Vitest + React Testing Library + jsdom + axios-mock-adapter. See [Testing Overview](../testing/overview.md) for the full breakdown and known coverage gaps.
