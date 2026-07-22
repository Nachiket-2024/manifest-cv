import { useQuery } from "@tanstack/react-query";

import { listApplicationsApi, getApplicationApi, type ApplicationRead, type ApplicationDetailRead } from "../api/application_api";

export const APPLICATIONS_QUERY_KEY = ["applications"] as const;
// "list" disambiguates this from applicationQueryKey(applicationId) below —
// see resumeQueries.ts's identical comment for why.
export const applicationsListQueryKey = (limit: number, offset: number) =>
    ["applications", "list", limit, offset] as const;
export const applicationQueryKey = (applicationId: number) => ["applications", applicationId] as const;

export const APPLICATIONS_PAGE_SIZE = 20;

export function useApplicationsQuery(limit = APPLICATIONS_PAGE_SIZE, offset = 0) {
    return useQuery<ApplicationRead[]>({
        queryKey: applicationsListQueryKey(limit, offset),
        queryFn: async () => (await listApplicationsApi(limit, offset)).data,
        placeholderData: (previousData) => previousData,
    });
}

export function useApplicationQuery(applicationId: number) {
    return useQuery<ApplicationDetailRead>({
        queryKey: applicationQueryKey(applicationId),
        queryFn: async () => (await getApplicationApi(applicationId)).data,
    });
}
