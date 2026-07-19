import { PERMISSIONS } from "../../authorization/permissions";

export interface NavItem {
    label: string;
    to: string;
    /** Omit for links every authenticated user should see regardless of permissions. */
    permission?: string;
}

/**
 * Single source of truth for the sidebar's link list. Items with a
 * `permission` are wrapped in IfCan by the Sidebar, so a caller who lacks
 * that permission simply never sees the link — the corresponding route is
 * still independently enforced by ProtectedRoute (and ultimately the
 * backend), this just keeps the nav from advertising pages a user can't
 * open.
 */
export const NAV_ITEMS: NavItem[] = [
    { label: "Dashboard", to: "/dashboard" },
    { label: "Users", to: "/users", permission: PERMISSIONS.USERS_LIST_ALL },
    { label: "Policies", to: "/policies", permission: PERMISSIONS.POLICIES_READ },

    // No permission required: every authenticated user has their own
    // private knowledge base (see App.tsx's /career-knowledge route).
    { label: "Career Knowledge", to: "/career-knowledge" },
    // No permission required: every authenticated user has their own
    // private resume drafts/applications (see App.tsx's /resumes and
    // /applications routes).
    { label: "Resumes", to: "/resumes" },
    { label: "Applications", to: "/applications" },

    // No permission required: every authenticated user can view their own
    // audit trail (GET /authorization/audit-log/me, GET /audit/security-log/me)
    // — the page itself additionally shows an "All Users" tab gated by
    // policies:read/security_audit:read for callers who hold those.
    { label: "Audit Log", to: "/audit-log" },
    { label: "Profile", to: "/profile" },
];
