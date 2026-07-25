import { api } from "../sdk";

export interface CareerKnowledgeBaseRead {
    id: number;
    raw_input: string;
    content: string;
    created_at: string;
    updated_at: string;
}

export interface CareerKnowledgeBaseCreatePayload {
    raw_input: string;
}

export interface CareerKnowledgeBaseUpdatePayload {
    raw_input?: string;
    content?: string;
}

export const getMyCareerKnowledgeBaseApi = () => api.get<CareerKnowledgeBaseRead>("/career-knowledge/");

export const createCareerKnowledgeBaseApi = (payload: CareerKnowledgeBaseCreatePayload) =>
    api.post<CareerKnowledgeBaseRead>("/career-knowledge/", payload);

export const updateCareerKnowledgeBaseApi = (payload: CareerKnowledgeBaseUpdatePayload) =>
    api.put<CareerKnowledgeBaseRead>("/career-knowledge/", payload);

export const deleteCareerKnowledgeBaseApi = () => api.delete("/career-knowledge/");
