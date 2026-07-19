import { useMutation } from "@tanstack/react-query";

import {
    createApplicationApi,
    updateApplicationApi,
    deleteApplicationApi,
    type ApplicationCreatePayload,
    type ApplicationUpdatePayload,
    type ApplicationDetailRead,
} from "../api/application_api";
import { extractApiErrorMessage } from "../api/apiError";
import { queryClient } from "../store/queryClient";
import { APPLICATIONS_QUERY_KEY, applicationQueryKey } from "./applicationQueries";

export function useCreateApplicationMutation() {
    return useMutation<ApplicationDetailRead, Error, ApplicationCreatePayload>({
        mutationFn: async (payload) => {
            try {
                return (await createApplicationApi(payload)).data;
            } catch (error) {
                throw new Error(extractApiErrorMessage(error, "Failed to save application"), { cause: error });
            }
        },
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: APPLICATIONS_QUERY_KEY });
            queryClient.setQueryData(applicationQueryKey(data.id), data);
        },
    });
}

export function useUpdateApplicationMutation(applicationId: number) {
    return useMutation<ApplicationDetailRead, Error, ApplicationUpdatePayload>({
        mutationFn: async (payload) => {
            try {
                return (await updateApplicationApi(applicationId, payload)).data;
            } catch (error) {
                throw new Error(extractApiErrorMessage(error, "Failed to update application"), { cause: error });
            }
        },
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: APPLICATIONS_QUERY_KEY });
            queryClient.setQueryData(applicationQueryKey(applicationId), data);
        },
    });
}

export function useDeleteApplicationMutation() {
    return useMutation<void, Error, number>({
        mutationFn: async (applicationId) => {
            try {
                await deleteApplicationApi(applicationId);
            } catch (error) {
                throw new Error(extractApiErrorMessage(error, "Failed to delete application"), { cause: error });
            }
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: APPLICATIONS_QUERY_KEY });
        },
    });
}
