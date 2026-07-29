import React, { Suspense, lazy } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from "react-router";
import { Flex, Heading, Text, VStack, Button } from "@chakra-ui/react";
import type { StackProps } from "@chakra-ui/react";

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
const ProfilePage = lazy(() => import("../mystic_auth/profile/ProfilePage"));

// ManifestCV's own domains — each user's private career knowledge base,
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

import { AppLayout, ProtectedRoute, PERMISSIONS, Toaster, useAuthStore, LoadingState } from "./sdk";
import type { NavItem } from "./sdk";

// ManifestCV's own sidebar links, added via AppLayout's extraNavItems prop
// rather than editing mystic_auth/layout/navItems.ts directly (that file
// stays upstream-owned — see
// docs/mystic_auth/template-usage/overview.md#shared-chrome-extension-points).
// No permission required on any of these: every authenticated user has
// their own private knowledge base, resume drafts, and applications.
// Ordered to land right after Dashboard (10) and before Users (20).
const EXTRA_NAV_ITEMS: NavItem[] = [
    { label: "Career Knowledge", to: "/career-knowledge", order: 12 },
    { label: "Resumes", to: "/resumes", order: 14 },
    { label: "Applications", to: "/applications", order: 16 },
];

const NotFoundPage: React.FC = () => {
    const navigate = useNavigate();
    return (
        <Flex align="center" justify="center" h="100vh" bg="bg.canvas" px={4} textAlign="center">
            <VStack {...({ spacing: 4 } as StackProps)}>
                <Heading color="fg.error" size="2xl">404</Heading>

                <Text fontSize="xl" fontWeight="medium">Oops! Page Not Found</Text>

                <Button
                    colorPalette="brand"
                    size="md"
                    fontWeight="bold"
                    onClick={() => navigate("/")}
                >
                    Go Home
                </Button>
            </VStack>
        </Flex>
    );
};

/**
 * NotAuthorizedPage
 * ----------------------------
 * The 403 page: where ProtectedRoute redirects an authenticated user who
 * lacks a route's required permission (see authorization/ProtectedRoute.tsx).
 * Deliberately a separate page from NotFoundPage: "you don't have
 * permission" and "this page doesn't exist" are different situations a
 * user shouldn't have to guess between.
 */
const NotAuthorizedPage: React.FC = () => {
    const navigate = useNavigate();
    return (
        <Flex align="center" justify="center" h="100vh" bg="bg.canvas" px={4} textAlign="center">
            <VStack {...({ spacing: 4 } as StackProps)}>
                <Heading color="fg.error" size="2xl">403</Heading>

                <Text fontSize="xl" fontWeight="medium">You don't have permission to view this page</Text>

                <Button
                    colorPalette="brand"
                    size="md"
                    fontWeight="bold"
                    onClick={() => navigate("/")}
                >
                    Go Home
                </Button>
            </VStack>
        </Flex>
    );
};

const App: React.FC = () => {
    useAuthSession();

    const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

    // isAuthenticated is null until the session check resolves; showing a
    // loading screen until then avoids a flash of unauthenticated content.
    if (isAuthenticated === null) {
        return <LoadingState message="Checking session..." fullScreen />;
    }

    return (
        <Router>
            {/* Toast queue renderer, mounted once at the app root (uses a
                Portal internally, so placement here doesn't affect layout) */}
            <Toaster />

            <Suspense fallback={<LoadingState message="Loading..." fullScreen />}>
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
                            <AppLayout extraNavItems={EXTRA_NAV_ITEMS}>
                                <DashboardPage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/users"
                    element={
                        <ProtectedRoute permission={PERMISSIONS.USERS_LIST_ALL}>
                            <AppLayout extraNavItems={EXTRA_NAV_ITEMS}>
                                <UsersPage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/policies"
                    element={
                        <ProtectedRoute permission={PERMISSIONS.POLICIES_READ}>
                            <AppLayout extraNavItems={EXTRA_NAV_ITEMS}>
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
                        <ProtectedRoute>
                            <AppLayout extraNavItems={EXTRA_NAV_ITEMS}>
                                <AuditLogPage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/profile"
                    element={
                        <ProtectedRoute>
                            <AppLayout extraNavItems={EXTRA_NAV_ITEMS}>
                                <ProfilePage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />

                {/* ManifestCV's own domains. No permission prop: every
                    authenticated user has their own private knowledge base,
                    resume drafts, and applications — ownership is enforced
                    server-side by user_id-scoped queries, not PBAC. */}
                <Route
                    path="/career-knowledge"
                    element={
                        <ProtectedRoute>
                            <AppLayout extraNavItems={EXTRA_NAV_ITEMS}>
                                <CareerKnowledgePage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/resumes"
                    element={
                        <ProtectedRoute>
                            <AppLayout extraNavItems={EXTRA_NAV_ITEMS}>
                                <ResumeDraftsPage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/resumes/:draftId"
                    element={
                        <ProtectedRoute>
                            <AppLayout extraNavItems={EXTRA_NAV_ITEMS}>
                                <ResumeEditorPage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/applications"
                    element={
                        <ProtectedRoute>
                            <AppLayout extraNavItems={EXTRA_NAV_ITEMS}>
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