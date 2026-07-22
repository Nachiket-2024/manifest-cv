import React, { useState } from "react";
import { Badge, Button, HStack, NativeSelect, Text } from "@chakra-ui/react";

import PageContainer from "../ui/PageContainer";
import DataTable, { type DataTableColumn } from "../ui/DataTable";
import ConfirmDialog from "../ui/ConfirmDialog";
import Pager from "../ui/Pager";
import { toaster } from "../ui/toasterInstance";
import { settings } from "../sdk";
import { useApplicationsQuery, APPLICATIONS_PAGE_SIZE } from "./applicationQueries";
import { useUpdateApplicationMutation, useDeleteApplicationMutation } from "./applicationMutations";
import { applicationPdfDownloadUrl, type ApplicationRead } from "../api/application_api";

const STATUS_OPTIONS = ["applied", "interviewing", "offered", "rejected"] as const;

/**
 * ApplicationsPage
 * ----------------------------
 * Tracked applications (claude.md flow steps 19-23) — each row is a
 * read-only snapshot of the resume actually sent (content + PDF), except
 * for status, which is expected to change over time as an application
 * progresses (see ApplicationRecord's docstring).
 */
const ApplicationsPage: React.FC = () => {
    const [offset, setOffset] = useState(0);
    const { data: applications, isLoading, isError } = useApplicationsQuery(APPLICATIONS_PAGE_SIZE, offset);
    const deleteMutation = useDeleteApplicationMutation();
    const [deletingApp, setDeletingApp] = useState<ApplicationRead | null>(null);

    const columns: DataTableColumn<ApplicationRead>[] = [
        { key: "company_name", header: "Company", render: (a) => <Text fontWeight="medium">{a.company_name}</Text> },
        { key: "application_date", header: "Date", render: (a) => a.application_date },
        { key: "application_time", header: "Time", render: (a) => a.application_time ?? "—" },
        {
            key: "status",
            header: "Status",
            render: (a) => <StatusCell application={a} />,
        },
        { key: "template", header: "Template", render: (a) => <Badge textTransform="capitalize">{a.template_id_snapshot}</Badge> },
        {
            key: "row_actions",
            header: "",
            align: "end",
            render: (a) => (
                <HStack justify="flex-end" gap={2}>
                    <Button asChild size="xs" variant="outline">
                        <a href={applicationPdfDownloadUrl(a.id, settings.apiBaseUrl)} target="_blank" rel="noreferrer">
                            PDF
                        </a>
                    </Button>
                    <Button size="xs" variant="outline" colorPalette="red" onClick={() => setDeletingApp(a)}>
                        Delete
                    </Button>
                </HStack>
            ),
        },
    ];

    const handleDeleteConfirm = () => {
        if (!deletingApp) return;
        // Same "step back a page instead of leaving the pager stuck on an
        // empty page" handling as ResumeDraftsPage.
        const isLastRowOnThisPage = applications?.length === 1 && offset > 0;
        deleteMutation.mutate(deletingApp.id, {
            onSuccess: () => {
                toaster.create({ title: "Application deleted", type: "success" });
                setDeletingApp(null);
                if (isLastRowOnThisPage) setOffset((prev) => Math.max(0, prev - APPLICATIONS_PAGE_SIZE));
            },
            onError: (error) => toaster.create({ title: error.message, type: "error" }),
        });
    };

    return (
        <PageContainer title="Applications" description="Every resume you've saved as a tracked application, with its status.">
            <DataTable
                columns={columns}
                rows={applications}
                rowKey={(a) => a.id}
                isLoading={isLoading}
                isError={isError}
                errorMessage="Failed to load applications"
                emptyMessage="No applications saved yet — finalize a resume to save one"
            />
            <Pager offset={offset} limit={APPLICATIONS_PAGE_SIZE} rowCount={applications?.length} onOffsetChange={setOffset} />

            <ConfirmDialog
                isOpen={!!deletingApp}
                title="Delete application"
                description={`Remove the tracked application for "${deletingApp?.company_name}"? This only deletes the tracking record, not your resume drafts.`}
                confirmLabel="Delete"
                isLoading={deleteMutation.isPending}
                onConfirm={handleDeleteConfirm}
                onCancel={() => setDeletingApp(null)}
            />
        </PageContainer>
    );
};

const StatusCell: React.FC<{ application: ApplicationRead }> = ({ application }) => {
    const updateMutation = useUpdateApplicationMutation(application.id);

    return (
        <NativeSelect.Root size="sm" w="140px">
            <NativeSelect.Field
                value={application.status}
                onChange={(e) =>
                    updateMutation.mutate(
                        { status: e.target.value },
                        { onError: (error) => toaster.create({ title: error.message, type: "error" }) }
                    )
                }
            >
                {STATUS_OPTIONS.map((s) => (
                    <option key={s} value={s}>
                        {s}
                    </option>
                ))}
            </NativeSelect.Field>
            <NativeSelect.Indicator />
        </NativeSelect.Root>
    );
};

export default ApplicationsPage;
