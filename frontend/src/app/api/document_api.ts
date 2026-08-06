import { api } from "../sdk";

export interface TemplateInfo {
    id: string;
    label: string;
}

export interface ResumeDocumentRead {
    id: number;
    resume_draft_id: number;
    template_id: string;
    created_at: string;
    updated_at: string;
}

export const listResumeTemplatesApi = (draftId: number) =>
    api.get<TemplateInfo[]>(`/resumes/${draftId}/templates`);

// A missing VITE_API_BASE_URL at build time (unset env var in production)
// would otherwise silently produce a literal "undefined/resumes/..." URL.
// This fails loudly instead, at the point the URL is actually needed, so
// the real cause is obvious rather than a mysterious 404'd iframe/link.
function requireApiBaseUrl(apiBaseUrl: string): string {
    if (!apiBaseUrl) {
        throw new Error("VITE_API_BASE_URL is not configured — set it before building the frontend");
    }
    return apiBaseUrl;
}

// Fetched through axios (not used directly as an <iframe> src) specifically
// so the browser never frames the backend's own origin: mystic-auth's
// SecurityHeadersMiddleware unconditionally sends X-Frame-Options: DENY on
// every response, with no per-route opt-out (see
// docs/mystic_auth/security/hardening.md). A direct cross-origin iframe
// src pointing at this URL would render blank. Fetching the PDF bytes as a
// blob and handing the frontend's own `blob:` object URL to the <iframe>
// sidesteps this entirely: X-Frame-Options only governs framing of the
// original HTTP resource, not a same-origin blob URL created from its
// response body. Session auth still travels via the httpOnly cookie, same
// as every other axios call (see api/axiosInstance.ts).
export const fetchResumeTemplatePreviewBlob = async (draftId: number, templateId: string): Promise<Blob> => {
    const response = await api.get<Blob>(`/resumes/${draftId}/templates/${templateId}/preview`, {
        responseType: "blob",
    });
    return response.data;
};

export const finalizeResumeDocumentApi = (draftId: number, templateId: string) =>
    api.post<ResumeDocumentRead>(`/resumes/${draftId}/finalize`, { template_id: templateId });

export const getFinalizedResumeDocumentApi = (draftId: number) =>
    api.get<ResumeDocumentRead>(`/resumes/${draftId}/finalize`);

export const resumeDocumentDownloadUrl = (draftId: number, apiBaseUrl: string) =>
    `${requireApiBaseUrl(apiBaseUrl)}/resumes/${draftId}/finalize/download`;
