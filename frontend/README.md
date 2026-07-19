# Frontend

React 19 + TypeScript SPA built with Vite, Chakra UI v3, Zustand, and TanStack Query.

This is one piece of ManifestCV — see the repository root [`README.md`](../README.md) for the full quickstart (Docker and local setup), and [`docs/architecture/frontend.md`](../docs/architecture/frontend.md) for the module layout, routing, and state-management conventions used here.

## Scripts

```bash
npm run dev         # Vite dev server
npm run build        # tsc -b && vite build (production build)
npm run typecheck    # tsc --noEmit across app/node/test tsconfigs
npm run lint         # eslint over frontend/ and tests/frontend/
npm run test          # vitest run (no coverage)
npm run test:coverage # vitest run --coverage (thresholds enforced)
```

See [`docs/testing/overview.md`](../docs/testing/overview.md) for what each suite covers.
