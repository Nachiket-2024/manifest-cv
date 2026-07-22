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

// Used directly as an <iframe>/<embed> src rather than via axios — the
// browser's own PDF viewer renders the response, no JSON involved. Session
// auth travels via the httpOnly cookie (axiosInstance's withCredentials
// applies to axios calls only; the browser sends cookies on this request
// too since it's same-origin-through-the-dev-proxy / same site).
export const resumeTemplatePreviewUrl = (draftId: number, templateId: string, apiBaseUrl: string) =>
    `${apiBaseUrl}/resumes/${draftId}/templates/${templateId}/preview`;

export const finalizeResumeDocumentApi = (draftId: number, templateId: string) =>
    api.post<ResumeDocumentRead>(`/resumes/${draftId}/finalize`, { template_id: templateId });

export const getFinalizedResumeDocumentApi = (draftId: number) =>
    api.get<ResumeDocumentRead>(`/resumes/${draftId}/finalize`);

export const resumeDocumentDownloadUrl = (draftId: number, apiBaseUrl: string) =>
    `${apiBaseUrl}/resumes/${draftId}/finalize/download`;
