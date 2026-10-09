import React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, Plus, Trash2 } from "lucide-react";
import { useNavigate } from "react-router";
import { Button, Card, FormAlert, LoadingState, PageContainer, toaster } from "../sdk";
import { deleteBuilderWorkspaceApi, listBuilderWorkspacesApi } from "../api/resume_builder_api";

const ResumeWorkspacesPage: React.FC = () => {
    const navigate = useNavigate(); const client = useQueryClient();
    const workspaces = useQuery({ queryKey: ["resume-workspaces"], queryFn: async () => (await listBuilderWorkspacesApi()).data });
    const remove = useMutation({ mutationFn: deleteBuilderWorkspaceApi, onSuccess: () => client.invalidateQueries({ queryKey: ["resume-workspaces"] }), onError: () => toaster.create({ title: "Unable to delete workspace", type: "error" }) });
    return <PageContainer title="Resume Studio" description="Build a tailored resume for each opportunity." icon={FileText}>
        <Card className="mb-6 flex flex-col items-start justify-between gap-4 border border-border-card bg-gradient-to-br from-bg-surface to-bg-muted/60 p-6 shadow-sm sm:flex-row sm:items-center"><div><span className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-solid">Resume workspace</span><h2 className="mt-2 text-lg font-semibold">Start a new resume</h2><p className="mt-1 text-sm text-fg-muted">Add your content first, then choose the layout that suits it.</p></div><Button variant="brand" onClick={() => navigate("/resume-builder/new")}><Plus size={16} /> Create a resume</Button></Card>
        {workspaces.isLoading ? <LoadingState message="Loading workspaces..." /> : workspaces.isError ? <FormAlert status="error">Unable to load workspaces.</FormAlert> : workspaces.data?.length === 0 ? <Card className="p-8 text-center"><h2 className="font-semibold">No workspaces yet</h2><p className="mt-1 text-sm text-fg-muted">Create your first workspace and pick a template on the next screen.</p></Card> : <div className="grid gap-3">{workspaces.data?.map((workspace) => <Card key={workspace.id} className="flex items-center justify-between gap-4 p-4"><button className="min-w-0 flex-1 text-left" onClick={() => navigate(`/resume-builder/${workspace.id}`)}><h3 className="truncate font-semibold">{workspace.title}</h3><p className="mt-1 line-clamp-2 text-sm text-fg-muted">{workspace.job_description}</p><p className="mt-2 text-xs text-fg-muted">Updated {new Date(workspace.updated_at).toLocaleString()} · {workspace.status}</p></button><Button aria-label={`Delete ${workspace.title}`} onClick={() => { if (window.confirm("Delete this workspace?")) remove.mutate(workspace.id); }}><Trash2 size={16} /></Button></Card>)}</div>}
    </PageContainer>;
};
export default ResumeWorkspacesPage;
