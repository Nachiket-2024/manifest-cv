import { useQuery } from "@tanstack/react-query";

import { listResumeDraftsApi, getResumeDraftApi, type ResumeDraftRead } from "../api/resume_api";
import {
    listResumeTemplatesApi,
    getFinalizedResumeDocumentApi,
    fetchResumeTemplatePreviewBlob,
    type TemplateInfo,
    type ResumeDocumentRead,
} from "../api/document_api";
import axios from "axios";

export const RESUME_DRAFTS_QUERY_KEY = ["resume-drafts"] as const;
// "list" disambiguates this from resumeDraftQueryKey(draftId) below. Both
// share the "resume-drafts" prefix (so invalidating RESUME_DRAFTS_QUERY_KEY
// still catches every paginated page, same as before pagination existed),
// but "list" (a string) never collides with a numeric draftId.
export const resumeDraftsListQueryKey = (limit: number, offset: number) =>
    ["resume-drafts", "list", limit, offset] as const;
export const resumeDraftQueryKey = (draftId: number) => ["resume-drafts", draftId] as const;
export const resumeTemplatesQueryKey = (draftId: number) => ["resume-drafts", draftId, "templates"] as const;
export const resumeDocumentQueryKey = (draftId: number) => ["resume-drafts", draftId, "document"] as const;
export const resumeTemplatePreviewQueryKey = (draftId: number, templateId: string) =>
    ["resume-drafts", draftId, "template-preview", templateId] as const;

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
        // A non-numeric :draftId route param (stale bookmark, typo'd URL,
        // manual edit) produces NaN. Skip the fetch entirely rather than
        // send a doomed `/resumes/NaN` request and cache a NaN-keyed result.
        enabled: !Number.isNaN(draftId),
    });
}

export function useResumeTemplatesQuery(draftId: number, enabled: boolean) {
    return useQuery<TemplateInfo[]>({
        queryKey: resumeTemplatesQueryKey(draftId),
        queryFn: async () => (await listResumeTemplatesApi(draftId)).data,
        enabled,
    });
}

// Returns the raw Blob, not an object URL. Object URLs are a side effect
// (must be revoked) that doesn't belong in cached query data, which can be
// reused/replayed by the cache independently of any one component's
// lifetime. The caller derives (and revokes) its own object URL from the
// Blob via useMemo/useEffect instead.
export function useResumeTemplatePreviewQuery(draftId: number, templateId: string | null) {
    return useQuery<Blob>({
        queryKey: resumeTemplatePreviewQueryKey(draftId, templateId ?? ""),
        queryFn: () => fetchResumeTemplatePreviewBlob(draftId, templateId!),
        enabled: templateId !== null,
        // Every render freshly compiles the PDF server-side (no persistence,
        // see fetchResumeTemplatePreviewBlob's own docstring), so a cached
        // blob from a prior visit is never known-fresh against the resume's
        // current content.
        staleTime: 0,
        gcTime: 0,
        // staleTime: 0 means TanStack Query's default refetchOnWindowFocus
        // would otherwise re-trigger a full server-side tectonic recompile
        // (and flash the "Compiling preview..." loader) every time the tab
        // regains focus, even though the already-shown preview is still
        // correct. Recompiling here buys nothing over the already-rendered
        // blob, since nothing about the resume changed just by tabbing away.
        refetchOnWindowFocus: false,
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
