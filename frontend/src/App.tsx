import React, { Suspense, lazy } from "react";
import { BrowserRouter as Router, Routes, Route, useNavigate } from "react-router-dom";
import { Flex, Heading, Text, VStack, Button } from "@chakra-ui/react";
import type { StackProps } from "@chakra-ui/react";

// LoginPage is loaded eagerly — it's the most common entry point for an
// unauthenticated visitor, so it shouldn't show a loading flash of its own
// on top of App's own session-check gate. Every other route is route-level
// code-split via React.lazy: none of them are needed until their route is
// actually visited, and splitting them keeps the initial bundle (and every
// unauthenticated visitor's download) limited to auth + the app shell.
import LoginPage from "./auth/login/LoginPage";
const SignupPage = lazy(() => import("./auth/signup/SignupPage"));
const VerifyAccountPage = lazy(() => import("./auth/verify_account/VerifyAccountPage"));
const PasswordResetRequestPage = lazy(() => import("./auth/password_reset_request/PasswordResetRequestPage"));
const PasswordResetConfirmPage = lazy(() => import("./auth/password_reset_confirm/PasswordResetConfirmPage"));
const DashboardPage = lazy(() => import("./dashboard/DashboardPage"));
const UsersPage = lazy(() => import("./users/UsersPage"));
const PoliciesPage = lazy(() => import("./policies/PoliciesPage"));
const AuditLogPage = lazy(() => import("./audit_log/AuditLogPage"));
const ProfilePage = lazy(() => import("./profile/ProfilePage"));

// ManifestCV's own domains — each user's private career knowledge base,
// resume drafts, and job applications.
const CareerKnowledgePage = lazy(() => import("./career_knowledge/CareerKnowledgePage"));
const ResumeDraftsPage = lazy(() => import("./resumes/ResumeDraftsPage"));
const ResumeEditorPage = lazy(() => import("./resumes/ResumeEditorPage"));
const ApplicationsPage = lazy(() => import("./applications/ApplicationsPage"));

import AppLayout from "./layout/AppLayout";
import { ProtectedRoute, PERMISSIONS, useAuthStore } from "./sdk";

// Mounted once here so any component/thunk can call toaster.create({...})
// (see ui/toaster.tsx)
import { Toaster } from "./ui/toaster";

// Runs the current-user query once and mirrors it into the Zustand auth
// store (see its own docstring for why this must be called exactly once,
// here at the app root)
import { useAuthSession } from "./auth/current_user/useCurrentUserQuery";

import LoadingState from "./ui/LoadingState";

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
 * The 403 page — where ProtectedRoute redirects an authenticated user who
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
            {/* Toast queue renderer — mounted once at the app root (uses a
                Portal internally, so placement here doesn't affect layout) */}
            <Toaster />

            <Suspense fallback={<LoadingState message="Loading..." fullScreen />}>
            <Routes>
                {/* Protected routes require authentication. Each is wrapped
                    in AppLayout (sidebar + top bar) inside ProtectedRoute, so
                    the shell only ever renders once access has actually been
                    confirmed. */}
                <Route
                    path="/"
                    element={
                        <ProtectedRoute>
                            <AppLayout>
                                <DashboardPage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/dashboard"
                    element={
                        <ProtectedRoute>
                            <AppLayout>
                                <DashboardPage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/users"
                    element={
                        <ProtectedRoute permission={PERMISSIONS.USERS_LIST_ALL}>
                            <AppLayout>
                                <UsersPage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/policies"
                    element={
                        <ProtectedRoute permission={PERMISSIONS.POLICIES_READ}>
                            <AppLayout>
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
                            <AppLayout>
                                <AuditLogPage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/profile"
                    element={
                        <ProtectedRoute>
                            <AppLayout>
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
                            <AppLayout>
                                <CareerKnowledgePage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/resumes"
                    element={
                        <ProtectedRoute>
                            <AppLayout>
                                <ResumeDraftsPage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/resumes/:draftId"
                    element={
                        <ProtectedRoute>
                            <AppLayout>
                                <ResumeEditorPage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />
                <Route
                    path="/applications"
                    element={
                        <ProtectedRoute>
                            <AppLayout>
                                <ApplicationsPage />
                            </AppLayout>
                        </ProtectedRoute>
                    }
                />

                {/* Public routes - accessible without authentication */}
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