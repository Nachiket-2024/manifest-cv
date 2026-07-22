import { api } from "../sdk";

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

export const applicationPdfDownloadUrl = (applicationId: number, apiBaseUrl: string) =>
    `${apiBaseUrl}/applications/${applicationId}/pdf`;
