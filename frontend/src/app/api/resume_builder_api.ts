import { api } from "../sdk";
import type { ResumeDocument, ResumeRevision, ResumeTemplate, ResumeWorkspace } from "../resume_builder/resumeDocumentTypes";

export const listBuilderTemplatesApi = () => api.get<ResumeTemplate[]>("/resume-workspaces/templates");
export const getBuilderTemplateApi = (key: string) => api.get<{ version: number; name: string; description: string; notes: string; document: ResumeDocument }>(`/resume-workspaces/templates/${key}`);
export const createBuilderWorkspaceApi = (payload: { title: string; job_description: string; template_key: string }) => api.post<ResumeWorkspace>("/resume-workspaces", payload);
export const getBuilderWorkspaceApi = (id: number) => api.get<{ workspace: ResumeWorkspace; revision: ResumeRevision }>(`/resume-workspaces/${id}`);
export const listBuilderWorkspacesApi = (limit = 50) => api.get<ResumeWorkspace[]>("/resume-workspaces", { params: { limit } });
export const deleteBuilderWorkspaceApi = (id: number) => api.delete(`/resume-workspaces/${id}`);
export const saveBuilderDocumentApi = (id: number, document: ResumeDocument, expected_revision_id: number | null, change_kind = "manual_edit") =>
    api.put<ResumeRevision>(`/resume-workspaces/${id}/document`, { document, expected_revision_id, change_kind });
export const generateBuilderDocumentApi = (id: number) => api.post<ResumeRevision>(`/resume-workspaces/${id}/generate`);
export const queueBuilderGenerationApi = (id: number) => api.post<{ id: number; status: string }>(`/resume-workspaces/${id}/generate-job`);
export const queueBuilderExportApi = (id: number) => api.post<{ id: number; status: string }>(`/resume-workspaces/${id}/export-job`);
export const getBuilderJobApi = (id: number) => api.get<{ status: string; result_revision_id: number | null; error_message?: string }>(`/resume-jobs/${id}`);
export const downloadBuilderJobApi = (id: number) => api.get<Blob>(`/resume-jobs/${id}/download`, { responseType: "blob" });
export const refineBuilderDocumentApi = (id: number, prompt: string) => api.post<ResumeRevision>(`/resume-workspaces/${id}/refine`, { prompt });
export const previewBuilderRefinementApi = (id: number, prompt: string) => api.post<{ document: ResumeDocument; source_revision_id: number }>(`/resume-workspaces/${id}/refine/preview`, { prompt });
export const listBuilderRevisionsApi = (id: number) => api.get<ResumeRevision[]>(`/resume-workspaces/${id}/revisions`);
export const restoreBuilderRevisionApi = (id: number, revisionId: number) => api.post<ResumeRevision>(`/resume-workspaces/${id}/revisions/${revisionId}/restore`);
export const approveBuilderWorkspaceApi = (id: number) => api.post<ResumeWorkspace>(`/resume-workspaces/${id}/approve`);
export const exportBuilderWorkspaceApi = (id: number) => api.get<Blob>(`/resume-workspaces/${id}/export`, { responseType: "blob" });
