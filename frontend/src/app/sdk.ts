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

// Settings — add your own VITE_* fields to root .env.example and
// core/settings.ts, read them from here rather than import.meta.env
// directly at every call site
export { default as settings, APP_NAME } from "../mystic_auth/core/settings";

// Error monitoring — reports a caught-but-still-noteworthy error the same
// way an uncaught render error gets reported automatically (see
// ui/ErrorBoundary.tsx). A safe no-op when VITE_SENTRY_DSN is unset, see
// docs/mystic_auth/error-monitoring/overview.md
export { reportError } from "../mystic_auth/core/errorMonitoring";

// Shared UI primitives — used by every page-level component, template or
// not. Not part of the upstream template's own sdk.ts (its own pages import
// these directly, being inside mystic_auth/ already) — re-exported here so
// ManifestCV's own feature pages (career_knowledge/, resumes/,
// applications/) don't reach into mystic_auth/ui/ directly.
export { default as PageContainer } from "../mystic_auth/ui/PageContainer";
export { default as Card } from "../mystic_auth/ui/Card";
export { default as DataTable } from "../mystic_auth/ui/DataTable";
export type { DataTableColumn } from "../mystic_auth/ui/DataTable";
export { default as ConfirmDialog } from "../mystic_auth/ui/ConfirmDialog";
export { default as FormAlert } from "../mystic_auth/ui/FormAlert";
export { default as LoadingState } from "../mystic_auth/ui/LoadingState";
export { toaster } from "../mystic_auth/ui/toasterInstance";

// Shared form/navigation guard hook, not specific to the profile page it
// originated on
export { useUnsavedChangesWarning } from "../mystic_auth/profile/useUnsavedChangesWarning";
