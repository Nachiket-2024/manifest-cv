/**
 * App-specific extension surface (see docs/mystic_auth/template-usage/overview.md).
 *
 * This is the counterpart to sdk.ts: sdk.ts re-exports the template's own
 * building blocks, this file is where a project built on this template adds
 * its own re-exports for its own domain code, kept separate so template
 * updates never conflict with app-specific additions here.
 *
 * The generic UI primitives below live in mystic_auth/ui/ (no identity
 * concept of their own) but ManifestCV's own pages reuse them directly, so
 * they're re-exported here rather than reaching into mystic_auth/ui/*
 * directly from app/ code. Same rationale as everything in sdk.ts.
 */

export { default as PageContainer } from "../mystic_auth/ui/PageContainer";
export { default as Card } from "../mystic_auth/ui/Card";
export { default as DataTable } from "../mystic_auth/ui/DataTable";
export type { DataTableColumn } from "../mystic_auth/ui/DataTable";
export { default as ConfirmDialog } from "../mystic_auth/ui/ConfirmDialog";
export { default as FormAlert } from "../mystic_auth/ui/FormAlert";
export { default as LoadingState } from "../mystic_auth/ui/LoadingState";
export { default as TableActionButton } from "../mystic_auth/ui/TableActionButton";
export { default as StyledSelect } from "../mystic_auth/ui/StyledSelect";
export { toaster } from "../mystic_auth/ui/toaster/toasterInstance";

export { useUnsavedChangesWarning } from "../mystic_auth/account_settings/useUnsavedChangesWarning";
