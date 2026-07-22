import { useQuery } from "@tanstack/react-query";

import { listResumeDraftsApi, getResumeDraftApi, type ResumeDraftRead } from "../api/resume_api";
import { listResumeTemplatesApi, getFinalizedResumeDocumentApi, type TemplateInfo, type ResumeDocumentRead } from "../api/document_api";
import axios from "axios";

export const RESUME_DRAFTS_QUERY_KEY = ["resume-drafts"] as const;
// "list" disambiguates this from resumeDraftQueryKey(draftId) below — both
// share the "resume-drafts" prefix (so invalidating RESUME_DRAFTS_QUERY_KEY
// still catches every paginated page, same as before pagination existed),
// but "list" (a string) never collides with a numeric draftId.
export const resumeDraftsListQueryKey = (limit: number, offset: number) =>
    ["resume-drafts", "list", limit, offset] as const;
export const resumeDraftQueryKey = (draftId: number) => ["resume-drafts", draftId] as const;
export const resumeTemplatesQueryKey = (draftId: number) => ["resume-drafts", draftId, "templates"] as const;
export const resumeDocumentQueryKey = (draftId: number) => ["resume-drafts", draftId, "document"] as const;

export const RESUME_DRAFTS_PAGE_SIZE = 20;

export function useResumeDraftsQuery(limit = RESUME_DRAFTS_PAGE_SIZE, offset = 0) {
    return useQuery<ResumeDraftRead[]>({
        queryKey: resumeDraftsListQueryKey(limit, offset),
        queryFn: async () => (await listResumeDraftsApi(limit, offset)).data,
        placeholderData: (previousData) => previousData,
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
