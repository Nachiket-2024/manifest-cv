import React, { useState } from "react";
import { Badge, HStack, NativeSelect, Text } from "@chakra-ui/react";
import { useTranslation } from "react-i18next";

import Pager from "../ui/Pager";
import { settings } from "../sdk";
import {
    PageContainer,
    DataTable,
    type DataTableColumn,
    ConfirmDialog,
    TableActionButton,
    toaster,
} from "../app_sdk";
import { useApplicationsQuery, APPLICATIONS_PAGE_SIZE } from "./applicationQueries";
import { useUpdateApplicationMutation, useDeleteApplicationMutation } from "./applicationMutations";
import { applicationPdfDownloadUrl, type ApplicationRead } from "../api/application_api";

const STATUS_OPTIONS = ["applied", "interviewing", "offered", "rejected"] as const;

/**
 * ApplicationsPage
 * ----------------------------
 * Tracked applications. Each row is a read-only snapshot of the resume
 * actually sent (content + PDF), except for status, which is expected to
 * change over time as an application progresses (see ApplicationRecord's
 * docstring).
 */
const ApplicationsPage: React.FC = () => {
    const { t } = useTranslation("applications");
    const [offset, setOffset] = useState(0);
    const { data: applications, isLoading, isError } = useApplicationsQuery(APPLICATIONS_PAGE_SIZE, offset);
    const deleteMutation = useDeleteApplicationMutation();
    const [deletingApp, setDeletingApp] = useState<ApplicationRead | null>(null);

    const columns: DataTableColumn<ApplicationRead>[] = [
        { key: "company_name", header: t("columns.company"), render: (a) => <Text fontWeight="medium">{a.company_name}</Text> },
        { key: "application_date", header: t("columns.date"), render: (a) => a.application_date },
        { key: "application_time", header: t("columns.time"), render: (a) => a.application_time ?? "—" },
        {
            key: "status",
            header: t("columns.status"),
            render: (a) => <StatusCell application={a} />,
        },
        { key: "template", header: t("columns.template"), render: (a) => <Badge textTransform="capitalize">{a.template_id_snapshot}</Badge> },
        {
            key: "row_actions",
            header: "",
            align: "end",
            render: (a) => (
                <HStack justify="flex-end" gap={2}>
                    <TableActionButton asChild colorPalette="blue">
                        <a href={applicationPdfDownloadUrl(a.id, settings.apiBaseUrl)} target="_blank" rel="noreferrer">
                            {t("pdf")}
                        </a>
                    </TableActionButton>
                    <TableActionButton colorPalette="red" onClick={() => setDeletingApp(a)}>
                        {t("app_common:delete")}
                    </TableActionButton>
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
                toaster.create({ title: t("toast.deleted"), type: "success" });
                setDeletingApp(null);
                if (isLastRowOnThisPage) setOffset((prev) => Math.max(0, prev - APPLICATIONS_PAGE_SIZE));
            },
            onError: (error) => toaster.create({ title: error.message, type: "error" }),
        });
    };

    return (
        <PageContainer title={t("title")} description={t("description")}>
            <DataTable
                columns={columns}
                rows={applications}
                rowKey={(a) => a.id}
                isLoading={isLoading}
                isError={isError}
                errorMessage={t("loadError")}
                emptyMessage={t("empty")}
            />
            <Pager offset={offset} limit={APPLICATIONS_PAGE_SIZE} rowCount={applications?.length} onOffsetChange={setOffset} />

            <ConfirmDialog
                isOpen={!!deletingApp}
                title={t("deleteDialog.title")}
                description={t("deleteDialog.description", { company: deletingApp?.company_name })}
                confirmLabel={t("deleteDialog.confirm")}
                isLoading={deleteMutation.isPending}
                onConfirm={handleDeleteConfirm}
                onCancel={() => setDeletingApp(null)}
            />
        </PageContainer>
    );
};

const StatusCell: React.FC<{ application: ApplicationRead }> = ({ application }) => {
    const { t } = useTranslation("applications");
    const { t: tCommon } = useTranslation("app_common");
    const updateMutation = useUpdateApplicationMutation(application.id);
    // A native <select> immediately shows whatever the user picks, in the
    // browser's own DOM, regardless of whether the mutation it triggers
    // ever succeeds. React only rewrites that DOM value when the `value`
    // prop it's given actually changes between renders. Binding straight to
    // `application.status` (server data) meant a failed update left the
    // dropdown showing the rejected value indefinitely, since the server
    // data behind that prop never changed. Local state lets this optimistically
    // show the pick immediately, then roll back to the previous value on error.
    const [localStatus, setLocalStatus] = useState(application.status);
    const [prevServerStatus, setPrevServerStatus] = useState(application.status);

    // Same render-time sync pattern ResumeEditorPage uses for its content
    // field, not an effect: adopt the server's status when it actually
    // changes (a successful update landing, a background refetch). But
    // never while a mutation this cell itself started is still in flight.
    if (application.status !== prevServerStatus && !updateMutation.isPending) {
        setPrevServerStatus(application.status);
        setLocalStatus(application.status);
    }

    const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
        const nextStatus = e.target.value;
        const previousStatus = localStatus;
        setLocalStatus(nextStatus);
        updateMutation.mutate(
            { status: nextStatus },
            {
                onError: (error) => {
                    setLocalStatus(previousStatus);
                    toaster.create({ title: error.message, type: "error" });
                },
            }
        );
    };

    return (
        <NativeSelect.Root size="sm" w="140px" disabled={updateMutation.isPending}>
            <NativeSelect.Field
                aria-label={t("statusAriaLabel", { company: application.company_name })}
                value={localStatus}
                onChange={handleChange}
            >
                {STATUS_OPTIONS.map((s) => (
                    <option key={s} value={s}>
                        {tCommon(`status.${s}`)}
                    </option>
                ))}
            </NativeSelect.Field>
            <NativeSelect.Indicator />
        </NativeSelect.Root>
    );
};

export default ApplicationsPage;
