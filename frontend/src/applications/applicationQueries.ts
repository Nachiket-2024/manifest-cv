import { useQuery } from "@tanstack/react-query";

import { listApplicationsApi, getApplicationApi, type ApplicationRead, type ApplicationDetailRead } from "../api/application_api";

export const APPLICATIONS_QUERY_KEY = ["applications"] as const;
export const applicationQueryKey = (applicationId: number) => ["applications", applicationId] as const;

export function useApplicationsQuery() {
    return useQuery<ApplicationRead[]>({
        queryKey: APPLICATIONS_QUERY_KEY,
        queryFn: async () => (await listApplicationsApi()).data,
    });
}

export function useApplicationQuery(applicationId: number) {
    return useQuery<ApplicationDetailRead>({
        queryKey: applicationQueryKey(applicationId),
        queryFn: async () => (await getApplicationApi(applicationId)).data,
    });
}
