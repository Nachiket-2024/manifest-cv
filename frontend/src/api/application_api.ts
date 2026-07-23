import { api } from "../mystic_auth/sdk";

export interface ApplicationRead {
    id: number;
    company_name: string;
    application_date: string;
    application_time: string | null;
    status: string;
    template_id_snapshot: string;
    created_at: string;
    updated_at: string;
}

export interface ApplicationDetailRead extends ApplicationRead {
    resume_content_snapshot: string;
}

export interface ApplicationCreatePayload {
    resume_draft_id: number;
    company_name: string;
    application_date: string;
    application_time?: string | null;
    status: string;
}

export interface ApplicationUpdatePayload {
    company_name?: string;
    application_date?: string;
    application_time?: string | null;
    status?: string;
}

export const listApplicationsApi = (limit = 20, offset = 0) =>
    api.get<ApplicationRead[]>("/applications/", { params: { limit, offset } });

export const getApplicationApi = (applicationId: number) =>
    api.get<ApplicationDetailRead>(`/applications/${applicationId}`);

export const createApplicationApi = (payload: ApplicationCreatePayload) =>
    api.post<ApplicationDetailRead>("/applications/", payload);

export const updateApplicationApi = (applicationId: number, payload: ApplicationUpdatePayload) =>
    api.patch<ApplicationDetailRead>(`/applications/${applicationId}`, payload);

export const deleteApplicationApi = (applicationId: number) => api.delete(`/applications/${applicationId}`);

// A missing VITE_API_BASE_URL at build time would otherwise silently
// produce a literal "undefined/applications/.../pdf" URL — fail loudly here
// instead, at the point the URL is actually needed.
export const applicationPdfDownloadUrl = (applicationId: number, apiBaseUrl: string) => {
    if (!apiBaseUrl) {
        throw new Error("VITE_API_BASE_URL is not configured — set it before building the frontend");
    }
    return `${apiBaseUrl}/applications/${applicationId}/pdf`;
};
