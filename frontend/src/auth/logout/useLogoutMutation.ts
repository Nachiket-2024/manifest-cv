import { useMutation } from "@tanstack/react-query";

import { logoutApi } from "../../api/auth_api";
import { extractApiErrorMessage } from "../../api/apiError";
import { useAuthStore } from "../../store/authStore";
import { queryClient } from "../../store/queryClient";
import { CURRENT_USER_QUERY_KEY } from "../current_user/useCurrentUserQuery";
import type { LogoutResponse } from "./logout_types";

// A successful logout means the session is gone, so onSuccess marks the auth
// store unauthenticated immediately (rather than waiting on a currentUser
// refetch that would 401 by design) — setAuthenticated(false) also clears
// the cached profile/permissions (see store/authStore.ts) — and clears the
// cached profile from the query cache too. Deliberately `setAuthenticated(false)`,
// not `reset()`: `reset()` would put isAuthenticated back to null, which
// every ProtectedRoute-wrapped page reads as "still checking the session"
// (a loading spinner) rather than "log out now" (an immediate redirect).
export function useLogoutMutation() {
    return useMutation<LogoutResponse, Error, void>({
        mutationFn: async () => {
            try {
                const res = await logoutApi();
                return res.data;
            } catch (error) {
                throw new Error(extractApiErrorMessage(error, "Logout failed"), { cause: error });
            }
        },
        onSuccess: () => {
            useAuthStore.getState().setAuthenticated(false);
            queryClient.setQueryData(CURRENT_USER_QUERY_KEY, null);
        },
    });
}
