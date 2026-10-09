import React, { useEffect, useState } from "react";
import { ArrowLeft, Check, FileText } from "lucide-react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router";
import { Button, FormAlert, LoadingState, PageContainer, toaster } from "../sdk";
import { createBuilderWorkspaceApi, getBuilderTemplateApi, listBuilderTemplatesApi } from "../api/resume_builder_api";
import type { ResumeDocument, ResumeTemplate } from "./resumeDocumentTypes";
import TemplatePreview from "./TemplatePreview";

type TemplateWithDocument = ResumeTemplate & { document: ResumeDocument };
type SetupState = { title?: string; jobDescription?: string };

const ResumeTemplatePickerPage: React.FC = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const setup = (location.state ?? {}) as SetupState;
    const [selectedKey, setSelectedKey] = useState("classic_single_column");
    useEffect(() => {
        if (!setup.title || !setup.jobDescription) navigate("/resume-builder/new", { replace: true });
    }, [navigate, setup.title, setup.jobDescription]);
    const templates = useQuery({
        queryKey: ["resume-builder-templates-with-documents"],
        queryFn: async () => {
            const summaries = (await listBuilderTemplatesApi()).data;
            return (await Promise.all(summaries.map(async (summary) => ({ ...summary, document: (await getBuilderTemplateApi(summary.template_key)).data.document }))));
        },
    });
    const create = useMutation({
        mutationFn: () => createBuilderWorkspaceApi({ title: setup.title?.trim() || "My resume", job_description: setup.jobDescription?.trim() || "", template_key: selectedKey }),
        onSuccess: (result) => navigate(`/resume-builder/${result.data.id}`),
        onError: () => toaster.create({ title: "Unable to create resume", type: "error" }),
    });

    if (!setup.title || !setup.jobDescription) return null;

    return <PageContainer title="Choose a template" description="Preview the full structure, then start editing your resume." icon={FileText}>
        <div className="mb-5 flex items-center justify-between gap-3"><Button variant="ghost" onClick={() => navigate("/resume-builder/new", { state: setup })}><ArrowLeft size={16} /> Back to content</Button><span className="rounded-full bg-bg-muted px-3 py-1 text-xs font-semibold text-fg-muted">Step 2 of 2 · Choose your layout</span></div>
        {templates.isLoading ? <LoadingState message="Loading templates..." /> : templates.isError ? <FormAlert status="error">Unable to load templates.</FormAlert> : <div className="grid gap-6 lg:grid-cols-2">{templates.data?.map((template) => <TemplateChoice key={template.template_key} template={template} selected={template.template_key === selectedKey} onSelect={() => setSelectedKey(template.template_key)} />)}</div>}
        <div className="mt-6 flex justify-end"><Button variant="brand" loading={create.isPending} disabled={templates.isLoading || !selectedKey} onClick={() => create.mutate()}>Use this template <Check size={16} /></Button></div>
        {create.isError && <FormAlert status="error">Unable to create the resume. Try again.</FormAlert>}
    </PageContainer>;
};

const TemplateChoice: React.FC<{ template: TemplateWithDocument; selected: boolean; onSelect: () => void }> = ({ template, selected, onSelect }) => <button type="button" onClick={onSelect} className={`group rounded-xl border p-4 text-left transition ${selected ? "border-blue-600 ring-2 ring-blue-200 dark:border-blue-400 dark:ring-blue-950" : "border-gray-200 hover:border-blue-300 dark:border-slate-700 dark:hover:border-blue-700"}`} aria-pressed={selected}>
    <TemplatePreview template={template} compact />
    <div className="mt-4 flex items-start justify-between gap-3"><div><h2 className="font-semibold">{template.name}</h2><p className="mt-1 text-sm text-fg-muted">{template.description}</p></div>{selected && <Check className="mt-1 shrink-0 text-blue-600" size={18} />}</div>
    <p className="mt-3 text-xs text-fg-muted">{template.notes}</p>
</button>;

export default ResumeTemplatePickerPage;
