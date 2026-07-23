/**
 * Public extension surface for feature code built on top of this template
 * (see docs/template-usage.md).
 *
 * Import from HERE, not internal paths like "../authorization/useAuthorization"
 * directly — one file to discover what's available, and one file to reconcile
 * when pulling in upstream template updates instead of every call site.
 *
 * Everything below is a straight re-export; see the original module for the
 * "why" behind any given piece.
 */

// PBAC — see docs/authorization/architecture.md
export { PERMISSIONS } from "./authorization/permissions";
export type { PermissionValue } from "./authorization/permissions";
export { useAuthorization } from "./authorization/useAuthorization";
export { useCan, useAuthorized } from "./authorization/useCan";
export { Authorized } from "./authorization/Authorized";
export { IfCan } from "./authorization/IfCan";
export { default as ProtectedRoute } from "./authorization/ProtectedRoute";
export * as authorizationService from "./authorization/authorizationService";

// API layer — see docs/architecture/frontend.md#api-layer
export { default as api } from "./api/axiosInstance";
export { extractApiErrorMessage } from "./api/apiError";

// Session/client state
export { useAuthStore } from "./store/authStore";
export { queryClient } from "./core/queryClient";

// Settings — add your own VITE_* fields to frontend/.env.example and
// core/settings.ts, read them from here rather than import.meta.env
// directly at every call site
export { default as settings, APP_NAME } from "./core/settings";

// Error monitoring — reports a caught-but-still-noteworthy error the same
// way an uncaught render error gets reported automatically (see
// ui/ErrorBoundary.tsx). A safe no-op when VITE_SENTRY_DSN is unset, see
// docs/error-monitoring/overview.md
export { reportError } from "./core/errorMonitoring";

// Shared UI primitives — used by every page-level component, template or not
export { default as PageContainer } from "./ui/PageContainer";
export { default as Card } from "./ui/Card";
export { default as DataTable } from "./ui/DataTable";
export type { DataTableColumn } from "./ui/DataTable";
export { default as ConfirmDialog } from "./ui/ConfirmDialog";
export { default as FormAlert } from "./ui/FormAlert";
export { default as LoadingState } from "./ui/LoadingState";
export { toaster } from "./ui/toasterInstance";

// Shared form/navigation guard hook, not specific to the profile page it
// originated on
export { useUnsavedChangesWarning } from "./profile/useUnsavedChangesWarning";
