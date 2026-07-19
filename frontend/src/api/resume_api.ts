import api from "./axiosInstance";

export interface ResumeDraftRead {
    id: number;
    job_description: string;
    resume_content: string | null;
    status: "draft" | "approved";
    created_at: string;
    updated_at: string;
}

export interface ResumeDraftCreatePayload {
    job_description: string;
}

export interface ResumeDraftUpdatePayload {
    refinement_prompt?: string;
    content?: string;
}

export const listResumeDraftsApi = () => api.get<ResumeDraftRead[]>("/resumes/");

export const getResumeDraftApi = (draftId: number) => api.get<ResumeDraftRead>(`/resumes/${draftId}`);

export const createResumeDraftApi = (payload: ResumeDraftCreatePayload) =>
    api.post<ResumeDraftRead>("/resumes/", payload);

export const updateResumeDraftApi = (draftId: number, payload: ResumeDraftUpdatePayload) =>
    api.put<ResumeDraftRead>(`/resumes/${draftId}`, payload);

export const approveResumeDraftApi = (draftId: number) => api.post<ResumeDraftRead>(`/resumes/${draftId}/approve`);

export const deleteResumeDraftApi = (draftId: number) => api.delete(`/resumes/${draftId}`);
