/**
 * Public extension surface for feature code built on top of this template
 * (see docs/mystic_auth/template-usage.md).
 *
 * Import from HERE, not internal paths like "../authorization/useAuthorization"
 * directly — one file to discover what's available, and one file to reconcile
 * when pulling in upstream template updates instead of every call site.
 *
 * Everything below is a straight re-export; see the original module for the
 * "why" behind any given piece.
 *
 * DO NOT hand-edit this file. Treat it as a drop-in you receive from
 * upstream, not a place to add your own re-exports — this is the one file a
 * `scripts/sync-upstream.sh` sync is expected to touch, and local edits
 * here are exactly what turns that sync into a manual conflict instead of
 * applying cleanly. If you need your own re-exports for your own domain
 * code, add them to app_sdk.ts instead — it's the counterpart file kept
 * empty by upstream for exactly this purpose, so it never conflicts on a
 * sync.
 */

// PBAC — see docs/mystic_auth/authorization/architecture.md
export { PERMISSIONS } from "../mystic_auth/authorization/permissions";
export type { PermissionValue } from "../mystic_auth/authorization/permissions";
export { useAuthorization } from "../mystic_auth/authorization/useAuthorization";
export { useCan, useAuthorized } from "../mystic_auth/authorization/useCan";
export { Authorized } from "../mystic_auth/authorization/Authorized";
export { IfCan } from "../mystic_auth/authorization/IfCan";
export { default as ProtectedRoute } from "../mystic_auth/authorization/ProtectedRoute";
export * as authorizationService from "../mystic_auth/authorization/authorizationService";

// API layer — see docs/mystic_auth/architecture/frontend.md#api-layer
export { default as api } from "../mystic_auth/api/axiosInstance";
export { extractApiErrorMessage } from "../mystic_auth/api/apiError";

// Session/client state
export { useAuthStore } from "../mystic_auth/store/authStore";
export { queryClient } from "../mystic_auth/core/queryClient";

// Settings — add your own VITE_* fields to frontend/.env.example and
// core/settings.ts, read them from here rather than import.meta.env
// directly at every call site
export { default as settings, APP_NAME } from "../mystic_auth/core/settings";

// Error monitoring — reports a caught-but-still-noteworthy error the same
// way an uncaught render error gets reported automatically (see
// ui/ErrorBoundary.tsx). A safe no-op when VITE_SENTRY_DSN is unset, see
// docs/mystic_auth/error-monitoring/overview.md
export { reportError } from "../mystic_auth/core/errorMonitoring";
