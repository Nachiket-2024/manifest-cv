import React, { useState } from "react";
import { Badge, Button, HStack, Stack, Text, Textarea } from "@chakra-ui/react";
import { useNavigate } from "react-router";
import { useTranslation } from "react-i18next";

import Pager from "../ui/Pager";
import {
    PageContainer,
    Card,
    DataTable,
    type DataTableColumn,
    FormAlert,
    ConfirmDialog,
    TableActionButton,
    toaster,
    BRAND_SOLID_HOVER_PROPS,
} from "../app_sdk";
import { useResumeDraftsQuery, RESUME_DRAFTS_PAGE_SIZE } from "./resumeQueries";
import { useCreateResumeDraftMutation, useDeleteResumeDraftMutation } from "./resumeMutations";
import type { ResumeDraftRead } from "../api/resume_api";

/**
 * ResumeDraftsPage
 * ----------------------------
 * Paste a job description, which immediately triggers server-side
 * retrieval + AI generation. The create call takes a few seconds for
 * that reason, same shape as CareerKnowledgePage's create flow. Existing
 * drafts link through to ResumeEditorPage for editing, refinement,
 * approval, and finalization.
 */
const ResumeDraftsPage: React.FC = () => {
    const { t } = useTranslation("resumes");
    const navigate = useNavigate();
    const [offset, setOffset] = useState(0);
    const { data: drafts, isLoading, isError } = useResumeDraftsQuery(RESUME_DRAFTS_PAGE_SIZE, offset);
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
                    toaster.create({ title: t("drafts.toast.generated"), type: "success" });
                    setJobDescription("");
                    navigate(`/resumes/${data.id}`);
                },
            }
        );
    };

    const handleDeleteConfirm = () => {
        if (!deletingDraft) return;
        // Deleting the only row on a page beyond the first would otherwise
        // leave the pager stuck on a now-empty page. Step back one page
        // instead, same as ApplicationsPage's identical handling.
        const isLastRowOnThisPage = drafts?.length === 1 && offset > 0;
        deleteMutation.mutate(deletingDraft.id, {
            onSuccess: () => {
                toaster.create({ title: t("drafts.toast.deleted"), type: "success" });
                setDeletingDraft(null);
                if (isLastRowOnThisPage) setOffset((prev) => Math.max(0, prev - RESUME_DRAFTS_PAGE_SIZE));
            },
            onError: (error) => toaster.create({ title: error.message, type: "error" }),
        });
    };

    const columns: DataTableColumn<ResumeDraftRead>[] = [
        {
            key: "job_description",
            header: t("drafts.columns.jobDescription"),
            render: (d) => (
                <Text lineClamp={2} maxW="lg">
                    {d.job_description}
                </Text>
            ),
        },
        {
            key: "status",
            header: t("drafts.columns.status"),
            render: (d) => (
                <Badge colorPalette={d.status === "approved" ? "green" : "yellow"} textTransform="capitalize">
                    {t(`status.${d.status}`, d.status)}
                </Badge>
            ),
        },
        {
            key: "updated_at",
            header: t("drafts.columns.updated"),
            render: (d) => new Date(d.updated_at).toLocaleString(),
        },
        {
            key: "row_actions",
            header: "",
            align: "end",
            render: (d) => (
                <HStack justify="flex-end" gap={2}>
                    <TableActionButton colorPalette="blue" onClick={() => navigate(`/resumes/${d.id}`)}>
                        {t("drafts.open")}
                    </TableActionButton>
                    <TableActionButton colorPalette="red" onClick={() => setDeletingDraft(d)}>
                        {t("app_common:delete")}
                    </TableActionButton>
                </HStack>
            ),
        },
    ];

    return (
        <PageContainer
            title={t("drafts.title")}
            description={t("drafts.description")}
        >
            <Card p={6} mb={6}>
                <Text color="fg.muted" mb={4}>
                    {t("drafts.intro")}
                </Text>
                <Stack as="form" onSubmit={handleCreate} gap={4}>
                    <Textarea
                        value={jobDescription}
                        onChange={(e) => setJobDescription(e.target.value)}
                        placeholder={t("drafts.placeholder")}
                        rows={8}
                    />
                    {createMutation.isError && <FormAlert status="error">{createMutation.error.message}</FormAlert>}
                    <Button
                        type="submit"
                        colorPalette="brand"
                        alignSelf="flex-start"
                        loading={createMutation.isPending}
                        loadingText={t("drafts.generateLoading")}
                        disabled={!jobDescription.trim()}
                        {...BRAND_SOLID_HOVER_PROPS}
                    >
                        {t("drafts.generate")}
                    </Button>
                </Stack>
            </Card>

            <DataTable
                columns={columns}
                rows={drafts}
                rowKey={(d) => d.id}
                isLoading={isLoading}
                isError={isError}
                errorMessage={t("drafts.loadError")}
                emptyMessage={t("drafts.empty")}
            />
            <Pager offset={offset} limit={RESUME_DRAFTS_PAGE_SIZE} rowCount={drafts?.length} onOffsetChange={setOffset} />

            <ConfirmDialog
                isOpen={!!deletingDraft}
                title={t("drafts.deleteDialog.title")}
                description={t("drafts.deleteDialog.description")}
                confirmLabel={t("drafts.deleteDialog.confirm")}
                isLoading={deleteMutation.isPending}
                onConfirm={handleDeleteConfirm}
                onCancel={() => setDeletingDraft(null)}
            />
        </PageContainer>
    );
};

export default ResumeDraftsPage;
