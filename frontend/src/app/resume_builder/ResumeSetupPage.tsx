import React, { useState } from "react";
import { ArrowRight, FileText } from "lucide-react";
import { useLocation, useNavigate } from "react-router";
import { Button, Card, Input, PageContainer, Textarea } from "../sdk";

const ResumeSetupPage: React.FC = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const previous = (location.state ?? {}) as { title?: string; jobDescription?: string };
    const [title, setTitle] = useState(previous.title ?? "My resume");
    const [jobDescription, setJobDescription] = useState(previous.jobDescription ?? "");
    const canContinue = title.trim().length > 0 && jobDescription.trim().length > 0;

    return <PageContainer title="Set up your resume" description="Start with the opportunity you are targeting. You will choose a visual template next." icon={FileText}>
        <div className="grid max-w-5xl gap-6 lg:grid-cols-[minmax(0,1fr)_18rem]">
            <Card className="space-y-5 border border-border-card p-6 shadow-sm">
            <div><span className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-solid">Step 1 of 2</span><h2 className="mt-2 text-xl font-semibold">Target one opportunity</h2><p className="mt-1 max-w-xl text-sm text-fg-muted">Give the builder enough context to tailor your story. You can edit every field before exporting.</p></div>
            <Input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Resume title" aria-label="Resume title" />
            <Textarea value={jobDescription} onChange={(event) => setJobDescription(event.target.value)} placeholder="Paste the job description or describe the role you are targeting" rows={10} aria-label="Job description" />
            <div className="flex items-center justify-between gap-4 border-t border-border-card pt-4"><span className="text-xs text-fg-muted">Your original career profile stays unchanged.</span><Button variant="brand" disabled={!canContinue} onClick={() => navigate("/resume-builder/new/templates", { state: { title: title.trim(), jobDescription: jobDescription.trim() } })}>Choose a template <ArrowRight size={16} /></Button></div>
            </Card>
            <Card className="h-fit border border-border-card bg-bg-muted/50 p-5 shadow-sm"><h2 className="font-semibold">A good starting brief</h2><ul className="mt-3 space-y-3 text-sm text-fg-muted"><li><strong className="text-fg-default">Role:</strong> paste the target title.</li><li><strong className="text-fg-default">Context:</strong> include the key responsibilities.</li><li><strong className="text-fg-default">Focus:</strong> mention the skills you want to emphasize.</li></ul></Card>
        </div>
    </PageContainer>;
};

export default ResumeSetupPage;
