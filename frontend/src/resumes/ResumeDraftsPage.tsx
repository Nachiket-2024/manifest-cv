import React, { useState } from "react";
import { Badge, Button, HStack, Stack, Text, Textarea } from "@chakra-ui/react";
import { useNavigate } from "react-router-dom";

import PageContainer from "../components/ui/PageContainer";
import Card from "../components/ui/Card";
import DataTable, { type DataTableColumn } from "../components/ui/DataTable";
import FormAlert from "../components/ui/FormAlert";
import ConfirmDialog from "../components/ui/ConfirmDialog";
import { toaster } from "../components/ui/toasterInstance";
import { useResumeDraftsQuery } from "./resumeQueries";
import { useCreateResumeDraftMutation, useDeleteResumeDraftMutation } from "./resumeMutations";
import type { ResumeDraftRead } from "../api/resume_api";

/**
 * ResumeDraftsPage
 * ----------------------------
 * Entry point for claude.md's Phase 2 flow: paste a job description (step
 * 6), which immediately triggers server-side retrieval + AI generation
 * (steps 7-8) — the create call takes a few seconds for that reason, same
 * shape as CareerKnowledgePage's create flow. Existing drafts link through
 * to ResumeEditorPage for editing/refinement/approval/finalization.
 */
const ResumeDraftsPage: React.FC = () => {
    const navigate = useNavigate();
    const { data: drafts, isLoading, isError } = useResumeDraftsQuery();
    const createMutation = useCreateResumeDraftMutation();
    const deleteMutation = useDeleteResumeDraftMutation();

    const [jobDescription, setJobDescription] = useState("");
    const [deletingDraft, setDeletingDraft] = useState<ResumeDraftRead | null>(null);

    const handleCreate = (e: React.FormEvent) => {
        e.preventDefault();
        createMutation.mutate(
            { job_description: jobDescription },
            {
                onSuccess: (data) => {
                    toaster.create({ title: "Resume generated", type: "success" });
                    setJobDescription("");
                    navigate(`/resumes/${data.id}`);
                },
            }
        );
    };

    const handleDeleteConfirm = () => {
        if (!deletingDraft) return;
        deleteMutation.mutate(deletingDraft.id, {
            onSuccess: () => {
                toaster.create({ title: "Resume deleted", type: "success" });
                setDeletingDraft(null);
            },
            onError: (error) => toaster.create({ title: error.message, type: "error" }),
        });
    };

    const columns: DataTableColumn<ResumeDraftRead>[] = [
        {
            key: "job_description",
            header: "Job description",
            render: (d) => (
                <Text lineClamp={2} maxW="lg">
                    {d.job_description}
                </Text>
            ),
        },
        {
            key: "status",
            header: "Status",
            render: (d) => (
                <Badge colorPalette={d.status === "approved" ? "green" : "yellow"} textTransform="capitalize">
                    {d.status}
                </Badge>
            ),
        },
        {
            key: "updated_at",
            header: "Updated",
            render: (d) => new Date(d.updated_at).toLocaleString(),
        },
        {
            key: "row_actions",
            header: "",
            align: "end",
            render: (d) => (
                <HStack justify="flex-end" gap={2}>
                    <Button size="xs" variant="outline" onClick={() => navigate(`/resumes/${d.id}`)}>
                        Open
                    </Button>
                    <Button size="xs" variant="outline" colorPalette="red" onClick={() => setDeletingDraft(d)}>
                        Delete
                    </Button>
                </HStack>
            ),
        },
    ];

    return (
        <PageContainer
            title="Resumes"
            description="Paste a job description to generate a tailored resume from your knowledge base — nothing beyond what's already there is ever added."
        >
            <Card p={6} mb={6}>
                <Text color="fg.muted" mb={4}>
                    The AI matches this job description against your career knowledge base and drafts a resume
                    from what it finds. You can then edit or ask for changes before approving it.
                </Text>
                <Stack as="form" onSubmit={handleCreate} gap={4}>
                    <Textarea
                        value={jobDescription}
                        onChange={(e) => setJobDescription(e.target.value)}
                        placeholder="Paste the job description here..."
                        rows={8}
                    />
                    {createMutation.isError && <FormAlert status="error">{createMutation.error.message}</FormAlert>}
                    <Button
                        type="submit"
                        colorPalette="brand"
                        alignSelf="flex-start"
                        loading={createMutation.isPending}
                        loadingText="Generating resume..."
                        disabled={!jobDescription.trim()}
                    >
                        Generate resume
                    </Button>
                </Stack>
            </Card>

            <DataTable
                columns={columns}
                rows={drafts}
                rowKey={(d) => d.id}
                isLoading={isLoading}
                isError={isError}
                errorMessage="Failed to load resumes"
                emptyMessage="No resumes yet — paste a job description above to generate one"
            />

            <ConfirmDialog
                isOpen={!!deletingDraft}
                title="Delete resume"
                description="This permanently deletes this tailored resume draft."
                confirmLabel="Delete"
                isLoading={deleteMutation.isPending}
                onConfirm={handleDeleteConfirm}
                onCancel={() => setDeletingDraft(null)}
            />
        </PageContainer>
    );
};

export default ResumeDraftsPage;
