import React, { Suspense, lazy, useEffect, useState } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router";
import { useTranslation } from "react-i18next";
import { BookOpen, BriefcaseBusiness, FilePenLine } from "lucide-react";

// LoginPage loads eagerly since it's the most common entry point for an
// unauthenticated visitor and shouldn't flash on top of the session-check
// gate below. Every other route is lazy-loaded so the initial bundle stays
// limited to auth + the app shell.
import LoginPage from "../mystic_auth/auth/login/LoginPage";
import { trackedLazy } from "../mystic_auth/ui/routing/trackedLazy";
const LandingPage = trackedLazy(() => import("./landing_page/LandingPage"));
const SignupPage = trackedLazy(() => import("../mystic_auth/auth/signup/SignupPage"));
const VerifyAccountPage = trackedLazy(() => import("../mystic_auth/auth/verify_account/VerifyAccountPage"));
const PasswordResetRequestPage = trackedLazy(() => import("../mystic_auth/auth/password_reset_request/PasswordResetRequestPage"));
const PasswordResetConfirmPage = trackedLazy(() => import("../mystic_auth/auth/password_reset_confirm/PasswordResetConfirmPage"));
const ConfirmDeleteAccountPage = trackedLazy(() => import("../mystic_auth/account_settings/confirm_delete/ConfirmDeleteAccountPage"));
const DashboardPage = trackedLazy(() => import("../mystic_auth/dashboard/DashboardPage"));
const UsersPage = trackedLazy(() => import("../mystic_auth/users/UsersPage"));
const PoliciesPage = trackedLazy(() => import("../mystic_auth/policies/PoliciesPage"));
const PermissionsPage = trackedLazy(() => import("../mystic_auth/permissions/PermissionsPage"));
const RateLimitsPage = trackedLazy(() => import("../mystic_auth/rate_limits/RateLimitsPage"));
const AuditLogPage = trackedLazy(() => import("../mystic_auth/audit_log/AuditLogPage"));
const AccountSettingsPage = trackedLazy(() => import("../mystic_auth/account_settings/AccountSettingsPage"));
const NotFoundPage = trackedLazy(() => import("./status_pages/NotFoundPage"));
const NotAuthorizedPage = trackedLazy(() => import("./status_pages/NotAuthorizedPage"));
const PrivacyPolicyPage = trackedLazy(() => import("./legal/PrivacyPolicyPage"));
const TermsOfServicePage = trackedLazy(() => import("./legal/TermsOfServicePage"));

// ManifestCV's own domains. Each user's private career knowledge base,
// resume workspaces, and job applications.
const CareerKnowledgePage = lazy(() => import("./career_knowledge/CareerKnowledgePage"));
const ApplicationsPage = lazy(() => import("./applications/ApplicationsPage"));
const ResumeWorkspacesPage = lazy(() => import("./resume_builder/ResumeWorkspacesPage"));
const ResumeSetupPage = lazy(() => import("./resume_builder/ResumeSetupPage"));
const ResumeTemplatePickerPage = lazy(() => import("./resume_builder/ResumeTemplatePickerPage"));
const ResumeBuilderPage = lazy(() => import("./resume_builder/ResumeBuilderPage"));

// Runs the current-user query once and mirrors it into the Zustand auth
// store. Not re-exported from sdk.ts since it must only be called here,
// at the app root, not from arbitrary feature code.
import { useAuthSession } from "../mystic_auth/auth/current_user/useCurrentUserQuery";
// Real-time push for cross-tab/cross-device session revocation. Same
// "call once, at the app root" reasoning as useAuthSession above.
import { useSessionEventsStream } from "../mystic_auth/auth/session_lifecycle/useSessionEventsStream";

import { AppLayout, ProtectedRoute, PERMISSIONS, Toaster, useAuthStore, LoadingState, CommandPalette } from "./sdk";
import type { NavItem } from "./sdk";
import RouteProgressBar from "../mystic_auth/ui/routing/RouteProgressBar";
import RouteFadeIn from "../mystic_auth/ui/routing/RouteFadeIn";
import OfflineBanner from "../mystic_auth/ui/network/OfflineBanner";

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
    // their own private knowledge base, resume workspaces, and applications.
    // Ordered to land right after Dashboard (10) and before Users (20).
    // Memoized on `t` (which itself changes identity when the active
    // language changes) rather than a module-level constant, since labels
    // are now translated - but still the same stable reference across
    // re-renders within one language, matching AppLayout's "same reference
    // on every route" guidance above.
    const extraNavItems: NavItem[] = React.useMemo(
        () => [
            { label: t("nav.careerKnowledge"), to: "/career-knowledge", order: 12, icon: BookOpen },
            { label: t("nav.resumes"), to: "/resume-builder", order: 14, icon: FilePenLine },
            { label: t("nav.applications"), to: "/applications", order: 16, icon: BriefcaseBusiness },
        ],
        [t]
    );

    // Cmd+K / Ctrl+K quick-jump palette. Listener lives here (not inside
    // CommandPalette) so the shortcut is clearly global. Ignored while
    // unauthenticated since every palette destination is a protected route.
    const [isPaletteOpen, setIsPaletteOpen] = useState(false);
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (!isAuthenticated) return;
            if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
                e.preventDefault();
                setIsPaletteOpen((open) => !open);
            }
        };
        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [isAuthenticated]);

    // Passed to every AppLayout below so Navbar's search-bar trigger opens
    // the same palette instance the keydown listener above toggles.
    const openCommandPalette = () => setIsPaletteOpen(true);

    // isAuthenticated is null until the session check resolves; showing a
    // loading screen until then avoids a flash of unauthenticated content.
    if (isAuthenticated === null) {
        return <LoadingState message={t("loading.checkingSession")} fullScreen />;
    }

    return (
        <Router>
            {/* Toast queue renderer (uses a Portal, so placement here doesn't affect layout) */}
            <Toaster />

            {/* Top-of-viewport loading bar. Mounted here so it overlays the
                current page during a lazy-route navigation instead of the
                Suspense fallback below blanking it. */}
            <RouteProgressBar />

            {/* Fixed bottom banner reflecting networkStatusStore's isOnline
                flag, visible regardless of which page/dialog is on screen. */}
            <OfflineBanner />

            <CommandPalette isOpen={isPaletteOpen} onClose={() => setIsPaletteOpen(false)} extraNavItems={extraNavItems} />

            {/* react-router wraps navigation in React.startTransition, so a
                click to a not-yet-loaded lazy route defers instead of
                blanking the current page. The single HTML boot shell covers
                the initial session and first lazy-route load. */}
            <RouteFadeIn>
            <Suspense fallback={null}>
            <Routes>
                {/* Protected routes require authentication. Each wraps
                    AppLayout (sidebar + top bar) inside ProtectedRoute, so
                    the shell only renders once access is confirmed.

                    Adding your own feature routes? Give AppLayout an
                    `extraNavItems` prop (NavItem shape from sdk.ts, e.g.
                    `[{ label: "Projects", to: "/projects", permission:
                    APP_PERMISSIONS.PROJECTS_READ }]`) instead of editing the
                    upstream-owned mystic_auth/layout/app_layout/navItems.ts.
                    Define the array once above this Routes block and reuse
                    the same reference on every AppLayout usage, so the
                    sidebar doesn't reshape while navigating. Pass it to
                    CommandPalette too (plus `extraSearchItems` for
                    in-page content) so palette search matches the sidebar.
                    See docs/mystic_auth/template-usage/frontend-customization.md#shared-chrome-extension-points. */}
                {/* "/" is the pre-auth landing page, not a redirect into the
                    app - it self-redirects an already-signed-in visitor to
                    /dashboard, so Sidebar's active-item highlight only ever
                    has to match routes that render the app shell. */}
                <Route path="/" element={<LandingPage />} />
                <Route
                    path="/dashboard"
                    element={
                        <ProtectedRoute>
                            <AppLayout extraNavItems={extraNavItems} onOpenCommandPalette={openCommandPalette}>
                                <DashboardPage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/users"
                    element={
                        <ProtectedRoute permission={PERMISSIONS.USERS_LIST_ALL}>
                            <AppLayout extraNavItems={extraNavItems} onOpenCommandPalette={openCommandPalette}>
                                <UsersPage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/policies"
                    element={
                        // Any of read/create, not read alone - see
                        // navItems.ts's matching Policies entry for why.
                        <ProtectedRoute permission={[PERMISSIONS.POLICIES_READ, PERMISSIONS.POLICIES_CREATE]}>
                            <AppLayout extraNavItems={extraNavItems} onOpenCommandPalette={openCommandPalette}>
                                <PoliciesPage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/permissions"
                    element={
                        <ProtectedRoute permission={PERMISSIONS.PERMISSIONS_READ}>
                            <AppLayout extraNavItems={extraNavItems} onOpenCommandPalette={openCommandPalette}>
                                <PermissionsPage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/rate-limits"
                    element={
                        <ProtectedRoute permission={PERMISSIONS.RATE_LIMITS_READ}>
                            <AppLayout extraNavItems={extraNavItems} onOpenCommandPalette={openCommandPalette}>
                                <RateLimitsPage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/audit-log"
                    element={
                        // No permission prop: every authenticated user can see
                        // their own audit trail (the "All users" tab is gated
                        // separately, see AuditLogPage). Added your own PBAC
                        // resource types/actions? Pass AuditLogPage
                        // `extraResourceTypes`/`extraActions` instead of
                        // hand-editing authorizationLogResourceTypes.ts.
                        <ProtectedRoute>
                            <AppLayout extraNavItems={extraNavItems} onOpenCommandPalette={openCommandPalette}>
                                <AuditLogPage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/account-settings"
                    element={
                        <ProtectedRoute>
                            <AppLayout extraNavItems={extraNavItems} onOpenCommandPalette={openCommandPalette}>
                                <AccountSettingsPage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />

                {/* ManifestCV's own domains have no permission prop. Every authenticated
                    user has their own private knowledge base, resume workspaces, and
                    applications, with ownership enforced server-side by user_id-scoped
                    queries rather than PBAC. */}
                <Route
                    path="/career-knowledge"
                    element={
                        <ProtectedRoute>
                            <AppLayout extraNavItems={extraNavItems} onOpenCommandPalette={openCommandPalette}>
                                <CareerKnowledgePage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/resume-builder"
                    element={
                        <ProtectedRoute>
                            <AppLayout extraNavItems={extraNavItems} onOpenCommandPalette={openCommandPalette}>
                                <ResumeWorkspacesPage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/resume-builder/new"
                    element={
                        <ProtectedRoute>
                            <AppLayout extraNavItems={extraNavItems} onOpenCommandPalette={openCommandPalette}>
                                <ResumeSetupPage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/resume-builder/new/templates"
                    element={
                        <ProtectedRoute>
                            <AppLayout extraNavItems={extraNavItems} onOpenCommandPalette={openCommandPalette}>
                                <ResumeTemplatePickerPage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/resume-builder/:workspaceId"
                    element={
                        <ProtectedRoute>
                            <AppLayout extraNavItems={extraNavItems} onOpenCommandPalette={openCommandPalette}>
                                <ResumeBuilderPage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/applications"
                    element={
                        <ProtectedRoute>
                            <AppLayout extraNavItems={extraNavItems} onOpenCommandPalette={openCommandPalette}>
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

                {/* Matches account_deletion_service.py's deletion_url */}
                <Route path="/confirm-delete" element={<ConfirmDeleteAccountPage />} />

                <Route path="/privacy" element={<PrivacyPolicyPage />} />
                <Route path="/terms" element={<TermsOfServicePage />} />

                {/* Where ProtectedRoute sends an authenticated user who lacks
                    a route's required permission */}
                <Route path="/not-authorized" element={<NotAuthorizedPage />} />

                <Route path="*" element={<NotFoundPage />} />
            </Routes>
            </Suspense>
            </RouteFadeIn>
        </Router>
    );
};

export default App;
