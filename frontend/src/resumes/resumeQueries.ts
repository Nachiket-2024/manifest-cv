import { useQuery } from "@tanstack/react-query";

import { listResumeDraftsApi, getResumeDraftApi, type ResumeDraftRead } from "../api/resume_api";
import { listResumeTemplatesApi, getFinalizedResumeDocumentApi, type TemplateInfo, type ResumeDocumentRead } from "../api/document_api";
import axios from "axios";

export const RESUME_DRAFTS_QUERY_KEY = ["resume-drafts"] as const;
export const resumeDraftQueryKey = (draftId: number) => ["resume-drafts", draftId] as const;
export const resumeTemplatesQueryKey = (draftId: number) => ["resume-drafts", draftId, "templates"] as const;
export const resumeDocumentQueryKey = (draftId: number) => ["resume-drafts", draftId, "document"] as const;

export function useResumeDraftsQuery() {
    return useQuery<ResumeDraftRead[]>({
        queryKey: RESUME_DRAFTS_QUERY_KEY,
        queryFn: async () => (await listResumeDraftsApi()).data,
    });
}

export function useResumeDraftQuery(draftId: number) {
    return useQuery<ResumeDraftRead>({
        queryKey: resumeDraftQueryKey(draftId),
        queryFn: async () => (await getResumeDraftApi(draftId)).data,
    });
}

export function useResumeTemplatesQuery(draftId: number, enabled: boolean) {
    return useQuery<TemplateInfo[]>({
        queryKey: resumeTemplatesQueryKey(draftId),
        queryFn: async () => (await listResumeTemplatesApi(draftId)).data,
        enabled,
    });
}

export function useFinalizedResumeDocumentQuery(draftId: number, enabled: boolean) {
    return useQuery<ResumeDocumentRead | null>({
        queryKey: resumeDocumentQueryKey(draftId),
        queryFn: async () => {
            try {
                return (await getFinalizedResumeDocumentApi(draftId)).data;
            } catch (error) {
                // No finalized document yet is an expected state before the
                // user picks a template, not a fetch failure.
                if (axios.isAxiosError(error) && error.response?.status === 404) {
                    return null;
                }
                throw error;
            }
        },
        enabled,
    });
}
