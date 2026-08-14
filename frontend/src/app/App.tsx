import React, { Suspense, lazy } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router";
import { useTranslation } from "react-i18next";

// LoginPage is loaded eagerly since it's the most common entry point for an
// unauthenticated visitor, so it shouldn't show a loading flash of its own
// on top of App's own session-check gate. Every other route is route-level
// code-split via React.lazy: none of them are needed until their route is
// actually visited, and splitting them keeps the initial bundle (and every
// unauthenticated visitor's download) limited to auth + the app shell.
import LoginPage from "../mystic_auth/auth/login/LoginPage";
const SignupPage = lazy(() => import("../mystic_auth/auth/signup/SignupPage"));
const VerifyAccountPage = lazy(() => import("../mystic_auth/auth/verify_account/VerifyAccountPage"));
const PasswordResetRequestPage = lazy(() => import("../mystic_auth/auth/password_reset_request/PasswordResetRequestPage"));
const PasswordResetConfirmPage = lazy(() => import("../mystic_auth/auth/password_reset_confirm/PasswordResetConfirmPage"));
const DashboardPage = lazy(() => import("../mystic_auth/dashboard/DashboardPage"));
const UsersPage = lazy(() => import("../mystic_auth/users/UsersPage"));
const PoliciesPage = lazy(() => import("../mystic_auth/policies/PoliciesPage"));
const AuditLogPage = lazy(() => import("../mystic_auth/audit_log/AuditLogPage"));
const AccountSettingsPage = lazy(() => import("../mystic_auth/account_settings/AccountSettingsPage"));
const NotFoundPage = lazy(() => import("../mystic_auth/status_pages/NotFoundPage"));
const NotAuthorizedPage = lazy(() => import("../mystic_auth/status_pages/NotAuthorizedPage"));

// ManifestCV's own domains. Each user's private career knowledge base,
// resume drafts, and job applications.
const CareerKnowledgePage = lazy(() => import("./career_knowledge/CareerKnowledgePage"));
const ResumeDraftsPage = lazy(() => import("./resumes/ResumeDraftsPage"));
const ResumeEditorPage = lazy(() => import("./resumes/ResumeEditorPage"));
const ApplicationsPage = lazy(() => import("./applications/ApplicationsPage"));

// Runs the current-user query once and mirrors it into the Zustand auth
// store (see its own docstring for why this must be called exactly once,
// here at the app root), not re-exported from sdk.ts since it's meant to
// be called exactly once, here, not from arbitrary feature code.
import { useAuthSession } from "../mystic_auth/auth/current_user/useCurrentUserQuery";
// Real-time push for cross-tab/cross-device session revocation, same
// "call exactly once, at the app root" reasoning as useAuthSession above.
import { useSessionEventsStream } from "../mystic_auth/auth/session_lifecycle/useSessionEventsStream";

import { AppLayout, ProtectedRoute, PERMISSIONS, Toaster, useAuthStore, LoadingState } from "./sdk";
import type { NavItem } from "./sdk";

const App: React.FC = () => {
    const { t } = useTranslation("app_common");
    useAuthSession();
    useSessionEventsStream();

    const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

    // ManifestCV's own sidebar links, added via AppLayout's extraNavItems prop
    // rather than editing mystic_auth/layout/navItems.ts directly (that file
    // stays upstream-owned. See
    // docs/mystic_auth/template-usage/overview.md#shared-chrome-extension-points).
    // No permission required on any of these: every authenticated user has
    // their own private knowledge base, resume drafts, and applications.
    // Ordered to land right after Dashboard (10) and before Users (20).
    // Memoized on `t` (which itself changes identity when the active
    // language changes) rather than a module-level constant, since labels
    // are now translated — but still the same stable reference across
    // re-renders within one language, matching AppLayout's "same reference
    // on every route" guidance above.
    const extraNavItems: NavItem[] = React.useMemo(
        () => [
            { label: t("nav.careerKnowledge"), to: "/career-knowledge", order: 12 },
            { label: t("nav.resumes"), to: "/resumes", order: 14 },
            { label: t("nav.applications"), to: "/applications", order: 16 },
        ],
        [t]
    );

    // isAuthenticated is null until the session check resolves. Showing a
    // loading screen until then avoids a flash of unauthenticated content.
    if (isAuthenticated === null) {
        return <LoadingState message={t("loading.checkingSession")} fullScreen />;
    }

    return (
        <Router>
            {/* Toast queue renderer, mounted once at the app root (uses a
                Portal internally, so placement here doesn't affect layout) */}
            <Toaster />

            <Suspense fallback={<LoadingState message={t("loading.loadingApp")} fullScreen />}>
            <Routes>
                {/* Protected routes require authentication. Each is wrapped
                    in AppLayout (sidebar + top bar) inside ProtectedRoute, so
                    the shell only ever renders once access has actually been
                    confirmed.

                    Adding your own feature routes? Give AppLayout an
                    `extraNavItems` prop (same NavItem shape as sdk.ts's
                    NavItem, e.g. `[{ label: "Projects", to: "/projects",
                    permission: APP_PERMISSIONS.PROJECTS_READ }]`) instead of
                    editing mystic_auth/layout/navItems.ts, since that file stays
                    upstream-owned. Define the array once above this Routes
                    block and pass the same reference to every AppLayout
                    usage, so the sidebar doesn't reshape as the user
                    navigates. See
                    docs/mystic_auth/template-usage/overview.md#shared-chrome-extension-points. */}
                {/* "/" itself is never a real page: redirect to "/dashboard"
                    so the URL and the Sidebar's active-item highlight (which
                    matches against "/dashboard") both stay correct. */}
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route
                    path="/dashboard"
                    element={
                        <ProtectedRoute>
                            <AppLayout extraNavItems={extraNavItems}>
                                <DashboardPage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/users"
                    element={
                        <ProtectedRoute permission={PERMISSIONS.USERS_LIST_ALL}>
                            <AppLayout extraNavItems={extraNavItems}>
                                <UsersPage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/policies"
                    element={
                        <ProtectedRoute permission={PERMISSIONS.POLICIES_READ}>
                            <AppLayout extraNavItems={extraNavItems}>
                                <PoliciesPage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/audit-log"
                    element={
                        // No permission prop: every authenticated user can see
                        // their own audit trail (see AuditLogPage's docstring
                        // for how the "All users" tab is gated separately).
                        //
                        // Added your own PBAC resource types or actions for
                        // your own business domain? Give AuditLogPage
                        // `extraResourceTypes`/`extraActions` (string[]) so
                        // they show up in the "Authorization decisions"
                        // filter dropdowns too, instead of hand-editing
                        // mystic_auth/audit_log/authorization_log/authorizationLogResourceTypes.ts.
                        // See
                        // docs/mystic_auth/template-usage/overview.md#shared-chrome-extension-points.
                        <ProtectedRoute>
                            <AppLayout extraNavItems={extraNavItems}>
                                <AuditLogPage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/account-settings"
                    element={
                        <ProtectedRoute>
                            <AppLayout extraNavItems={extraNavItems}>
                                <AccountSettingsPage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />

                {/* ManifestCV's own domains have no permission prop. Every authenticated
                    user has their own private knowledge base, resume drafts, and
                    applications, with ownership enforced server-side by user_id-scoped
                    queries rather than PBAC. */}
                <Route
                    path="/career-knowledge"
                    element={
                        <ProtectedRoute>
                            <AppLayout extraNavItems={extraNavItems}>
                                <CareerKnowledgePage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/resumes"
                    element={
                        <ProtectedRoute>
                            <AppLayout extraNavItems={extraNavItems}>
                                <ResumeDraftsPage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/resumes/:draftId"
                    element={
                        <ProtectedRoute>
                            <AppLayout extraNavItems={extraNavItems}>
                                <ResumeEditorPage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/applications"
                    element={
                        <ProtectedRoute>
                            <AppLayout extraNavItems={extraNavItems}>
                                <ApplicationsPage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />

                <Route path="/login" element={<LoginPage />} />
                <Route path="/signup" element={<SignupPage />} />
                <Route path="/verify-account" element={<VerifyAccountPage />} />
                <Route path="/password-reset-request" element={<PasswordResetRequestPage />} />

                {/* Matches backend email link format */}
                <Route path="/reset-password" element={<PasswordResetConfirmPage />} />

                {/* Where ProtectedRoute sends an authenticated user who lacks
                    a route's required permission */}
                <Route path="/not-authorized" element={<NotAuthorizedPage />} />

                <Route path="*" element={<NotFoundPage />} />
            </Routes>
            </Suspense>
        </Router>
    );
};

export default App;