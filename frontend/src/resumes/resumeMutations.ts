import { useMutation } from "@tanstack/react-query";

import {
    createResumeDraftApi,
    updateResumeDraftApi,
    approveResumeDraftApi,
    deleteResumeDraftApi,
    type ResumeDraftCreatePayload,
    type ResumeDraftUpdatePayload,
    type ResumeDraftRead,
} from "../api/resume_api";
import { finalizeResumeDocumentApi, type ResumeDocumentRead } from "../api/document_api";
import { extractApiErrorMessage, queryClient } from "../mystic_auth/sdk";
import { RESUME_DRAFTS_QUERY_KEY, resumeDraftQueryKey, resumeDocumentQueryKey } from "./resumeQueries";

export function useCreateResumeDraftMutation() {
    return useMutation<ResumeDraftRead, Error, ResumeDraftCreatePayload>({
        mutationFn: async (payload) => {
            try {
                return (await createResumeDraftApi(payload)).data;
            } catch (error) {
                throw new Error(extractApiErrorMessage(error, "Failed to generate resume"), { cause: error });
            }
        },
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: RESUME_DRAFTS_QUERY_KEY });
            queryClient.setQueryData(resumeDraftQueryKey(data.id), data);
        },
    });
}

export function useUpdateResumeDraftMutation(draftId: number) {
    return useMutation<ResumeDraftRead, Error, ResumeDraftUpdatePayload>({
        mutationFn: async (payload) => {
            try {
                return (await updateResumeDraftApi(draftId, payload)).data;
            } catch (error) {
                throw new Error(extractApiErrorMessage(error, "Failed to update resume"), { cause: error });
            }
        },
        onSuccess: (data) => {
            queryClient.setQueryData(resumeDraftQueryKey(draftId), data);
        },
    });
}

export function useApproveResumeDraftMutation(draftId: number) {
    return useMutation<ResumeDraftRead, Error, void>({
        mutationFn: async () => {
            try {
                return (await approveResumeDraftApi(draftId)).data;
            } catch (error) {
                throw new Error(extractApiErrorMessage(error, "Failed to approve resume"), { cause: error });
            }
        },
        onSuccess: (data) => {
            queryClient.setQueryData(resumeDraftQueryKey(draftId), data);
        },
    });
}

export function useDeleteResumeDraftMutation() {
    return useMutation<void, Error, number>({
        mutationFn: async (draftId) => {
            try {
                await deleteResumeDraftApi(draftId);
            } catch (error) {
                throw new Error(extractApiErrorMessage(error, "Failed to delete resume"), { cause: error });
            }
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: RESUME_DRAFTS_QUERY_KEY });
        },
    });
}

export function useFinalizeResumeDocumentMutation(draftId: number) {
    return useMutation<ResumeDocumentRead, Error, string>({
        mutationFn: async (templateId) => {
            try {
                return (await finalizeResumeDocumentApi(draftId, templateId)).data;
            } catch (error) {
                throw new Error(extractApiErrorMessage(error, "Failed to generate the final PDF"), { cause: error });
            }
        },
        onSuccess: (data) => {
            queryClient.setQueryData(resumeDocumentQueryKey(draftId), data);
        },
    });
}
