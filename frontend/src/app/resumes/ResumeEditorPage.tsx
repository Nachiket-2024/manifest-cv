import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { useTranslation } from "react-i18next";
import {
    Badge,
    Box,
    Button,
    Heading,
    HStack,
    Input,
    NativeSelect,
    Stack,
    Text,
    Textarea,
} from "@chakra-ui/react";

import { settings } from "../sdk";
import {
    PageContainer,
    Card,
    LoadingState,
    FormAlert,
    StyledSelect,
    toaster,
    useUnsavedChangesWarning,
    BRAND_SOLID_HOVER_PROPS,
    SECONDARY_BUTTON_PROPS,
} from "../app_sdk";

import {
    useResumeDraftQuery,
    useResumeTemplatesQuery,
    useResumeTemplatePreviewQuery,
    useFinalizedResumeDocumentQuery,
} from "./resumeQueries";
import {
    useUpdateResumeDraftMutation,
    useApproveResumeDraftMutation,
    useFinalizeResumeDocumentMutation,
} from "./resumeMutations";
import { resumeDocumentDownloadUrl } from "../api/document_api";
import { useCreateApplicationMutation } from "../applications/applicationMutations";

const APPLICATION_STATUS_OPTIONS = ["applied", "interviewing", "offered", "rejected"] as const;

/**
 * ResumeEditorPage
 * ----------------------------
 * One resume draft's full lifecycle: direct content edits or AI-driven
 * refinement while in "draft" status, then approval (locking content),
 * then template preview → finalize-to-PDF → save-as-tracked-application,
 * all against the one draft identified by the :draftId route param.
 */
const ResumeEditorPage: React.FC = () => {
    const { t } = useTranslation("resumes");
    const { t: tCommon } = useTranslation("app_common");
    const { draftId: draftIdParam } = useParams<{ draftId: string }>();
    const draftId = Number(draftIdParam);
    const navigate = useNavigate();

    const { data: draft, isLoading, isError } = useResumeDraftQuery(draftId);
    // Two independent mutation instances against the same PUT endpoint.
    // Save and refine are triggered by separate buttons/forms, so each needs
    // its own `isPending`/`isError` state rather than one clicking making
    // the other's button spin or show the wrong error.
    const updateMutation = useUpdateResumeDraftMutation(draftId);
    const refineMutation = useUpdateResumeDraftMutation(draftId);
    const approveMutation = useApproveResumeDraftMutation(draftId);

    const [content, setContent] = useState("");
    const [prevResumeContent, setPrevResumeContent] = useState<string | null | undefined>(undefined);
    const [refinementPrompt, setRefinementPrompt] = useState("");

    if (draft && draft.resume_content !== prevResumeContent) {
        setPrevResumeContent(draft.resume_content);
        setContent(draft.resume_content ?? "");
    }

    const isDirty = draft ? content !== (draft.resume_content ?? "") : false;
    useUnsavedChangesWarning(isDirty);

    const isApproved = draft?.status === "approved";

    const templatesQuery = useResumeTemplatesQuery(draftId, isApproved);
    const documentQuery = useFinalizedResumeDocumentQuery(draftId, isApproved);
    const finalizeMutation = useFinalizeResumeDocumentMutation(draftId);
    const createApplicationMutation = useCreateApplicationMutation();

    const [selectedTemplateOverride, setSelectedTemplateOverride] = useState<string | null>(null);
    const selectedTemplateId = selectedTemplateOverride ?? templatesQuery.data?.[0]?.id ?? null;
    const previewQuery = useResumeTemplatePreviewQuery(draftId, selectedTemplateId);
    const [companyName, setCompanyName] = useState("");
    const [applicationDate, setApplicationDate] = useState(() => new Date().toISOString().slice(0, 10));
    const [applicationTime, setApplicationTime] = useState("");
    const [applicationStatus, setApplicationStatus] = useState<string>("applied");

    // Hands the <iframe> a `blob:` object URL instead of the backend's own
    // cross-origin URL. See fetchResumeTemplatePreviewBlob's own docstring
    // for why a direct src no longer renders (mystic-auth's
    // SecurityHeadersMiddleware always sends X-Frame-Options: DENY now, with
    // no per-route opt-out). The object URL is a side effect of rendering
    // previewQuery.data, not itself query-cacheable state, so it's derived
    // here with useMemo (re-created only when the underlying Blob changes)
    // rather than duplicated into its own useState.
    const previewBlobUrl = React.useMemo(
        () => (previewQuery.data ? URL.createObjectURL(previewQuery.data) : null),
        [previewQuery.data]
    );
    useEffect(() => {
        // Revocation only. No setState here, so this never fights React's
        // effect-ordering guidance the way setting loading/data state
        // directly in an effect body would (see resumeQueries.ts's
        // useResumeTemplatePreviewQuery for where that state now lives).
        return () => {
            if (previewBlobUrl) URL.revokeObjectURL(previewBlobUrl);
        };
    }, [previewBlobUrl]);

    useEffect(() => {
        if (previewQuery.isError) {
            toaster.create({ title: "Failed to load template preview", type: "error" });
        }
    }, [previewQuery.isError]);

    const handleSave = (e: React.FormEvent) => {
        e.preventDefault();
        updateMutation.mutate(
            { content },
            { onSuccess: () => toaster.create({ title: t("editor.toast.saved"), type: "success" }) }
        );
    };

    const handleRefine = (e: React.FormEvent) => {
        e.preventDefault();
        refineMutation.mutate(
            { refinement_prompt: refinementPrompt },
            {
                onSuccess: () => {
                    toaster.create({ title: t("editor.toast.updated"), type: "success" });
                    setRefinementPrompt("");
                },
            }
        );
    };

    const handleApprove = () => {
        approveMutation.mutate(undefined, {
            onSuccess: () => toaster.create({ title: t("editor.toast.approved"), type: "success" }),
            onError: (error) => toaster.create({ title: error.message, type: "error" }),
        });
    };

    const handleFinalize = () => {
        if (!selectedTemplateId) return;
        finalizeMutation.mutate(selectedTemplateId, {
            onSuccess: () => toaster.create({ title: t("editor.toast.pdfGenerated"), type: "success" }),
            onError: (error) => toaster.create({ title: error.message, type: "error" }),
        });
    };

    const handleSaveApplication = (e: React.FormEvent) => {
        e.preventDefault();
        createApplicationMutation.mutate(
            {
                resume_draft_id: draftId,
                company_name: companyName,
                application_date: applicationDate,
                application_time: applicationTime || undefined,
                status: applicationStatus,
            },
            {
                onSuccess: () => {
                    toaster.create({ title: t("editor.toast.applicationSaved"), type: "success" });
                    navigate("/applications");
                },
                onError: (error) => toaster.create({ title: error.message, type: "error" }),
            }
        );
    };

    if (isLoading) {
        return (
            <PageContainer title={t("editor.title")}>
                <LoadingState message={t("editor.loading")} />
            </PageContainer>
        );
    }

    if (Number.isNaN(draftId)) {
        return (
            <PageContainer title={t("editor.title")}>
                <FormAlert status="error">{t("editor.invalidId")}</FormAlert>
            </PageContainer>
        );
    }

    if (isError || !draft) {
        return (
            <PageContainer title={t("editor.title")}>
                <FormAlert status="error">{t("editor.loadError")}</FormAlert>
            </PageContainer>
        );
    }

    return (
        <PageContainer
            title={t("editor.title")}
            description={t("editor.description")}
            actions={
                <Badge colorPalette={isApproved ? "green" : "yellow"} textTransform="capitalize" fontSize="sm">
                    {t(`status.${draft.status}`, draft.status)}
                </Badge>
            }
        >
            <Stack gap={6} maxW="3xl">
                <Card p={6}>
                    <Heading as="h3" size="sm" mb={2}>
                        {t("editor.jobDescriptionHeading")}
                    </Heading>
                    <Text color="fg.muted" whiteSpace="pre-wrap" fontSize="sm">
                        {draft.job_description}
                    </Text>
                </Card>

                <Card p={6}>
                    <Heading as="h3" size="sm" mb={4}>
                        {t("editor.contentHeading")}
                    </Heading>
                    <Stack as="form" onSubmit={handleSave} gap={4}>
                        <Textarea
                            value={content}
                            onChange={(e) => setContent(e.target.value)}
                            rows={20}
                            fontFamily="mono"
                            // Disabled during a refine call too, not just a
                            // save. Content is about to be overwritten by
                            // the AI's response, so editing it mid-flight
                            // would just be silently discarded when that
                            // response lands.
                            disabled={isApproved || updateMutation.isPending || refineMutation.isPending}
                        />
                        {updateMutation.isError && <FormAlert status="error">{updateMutation.error.message}</FormAlert>}
                        {!isApproved && (
                            <Button
                                type="submit"
                                colorPalette="brand"
                                alignSelf="flex-start"
                                loading={updateMutation.isPending}
                                disabled={!isDirty || !content.trim()}
                                {...BRAND_SOLID_HOVER_PROPS}
                            >
                                {t("editor.save")}
                            </Button>
                        )}
                    </Stack>
                </Card>

                {!isApproved && (
                    <Card p={6}>
                        <Heading as="h3" size="sm" mb={2}>
                            {t("editor.askForChange.heading")}
                        </Heading>
                        <Text color="fg.muted" mb={4} fontSize="sm">
                            {t("editor.askForChange.body")}
                        </Text>
                        <Stack as="form" onSubmit={handleRefine} gap={4}>
                            <Textarea
                                value={refinementPrompt}
                                onChange={(e) => setRefinementPrompt(e.target.value)}
                                placeholder={t("editor.askForChange.placeholder")}
                                rows={3}
                            />
                            {refineMutation.isError && <FormAlert status="error">{refineMutation.error.message}</FormAlert>}
                            <HStack>
                                <Button
                                    type="submit"
                                    {...SECONDARY_BUTTON_PROPS}
                                    loading={refineMutation.isPending}
                                    loadingText={t("editor.askForChange.refineLoading")}
                                    disabled={!refinementPrompt.trim() || isDirty}
                                    title={isDirty ? t("editor.askForChange.refineDisabledTitle") : undefined}
                                >
                                    {t("editor.askForChange.refine")}
                                </Button>
                                <Button
                                    colorPalette="brand"
                                    onClick={handleApprove}
                                    loading={approveMutation.isPending}
                                    disabled={!content.trim() || isDirty}
                                    title={isDirty ? t("editor.askForChange.approveDisabledTitle") : undefined}
                                    {...BRAND_SOLID_HOVER_PROPS}
                                >
                                    {t("editor.askForChange.approve")}
                                </Button>
                            </HStack>
                        </Stack>
                    </Card>
                )}

                {isApproved && (
                    <Card p={6}>
                        <Heading as="h3" size="sm" mb={2}>
                            {t("editor.template.heading")}
                        </Heading>
                        <Text color="fg.muted" mb={4} fontSize="sm">
                            {t("editor.template.body")}
                        </Text>

                        {templatesQuery.isLoading && <LoadingState message={t("editor.template.loading")} />}

                        {templatesQuery.isError && (
                            <FormAlert status="error">{t("editor.template.loadError")}</FormAlert>
                        )}

                        {templatesQuery.data && (
                            <Stack gap={4}>
                                <StyledSelect
                                    ariaLabel={t("editor.template.selectLabel")}
                                    w="200px"
                                    value={selectedTemplateId ?? ""}
                                    onChange={(value) => setSelectedTemplateOverride(value)}
                                    options={templatesQuery.data.map((tpl) => ({ label: tpl.label, value: tpl.id }))}
                                />

                                {selectedTemplateId && previewQuery.isFetching && (
                                    <LoadingState message={t("editor.template.compiling")} />
                                )}

                                {selectedTemplateId && !previewQuery.isFetching && previewBlobUrl && (
                                    // The preview itself is a printable document, always a
                                    // white page regardless of app theme, so a thin border
                                    // pulled from border.default (gray.700 on dark mode's
                                    // gray.800 Card, only one step apart) barely separated it
                                    // from the Card behind it. A visibly stronger border plus a
                                    // shadow instead, so the "page" reads as a distinct object
                                    // sitting on the surface in both modes, the same "raised
                                    // control" idiom SECONDARY_BUTTON_PROPS/TableActionButton
                                    // use for buttons.
                                    <Box
                                        borderWidth="1px"
                                        borderColor="gray.300"
                                        borderRadius="md"
                                        overflow="hidden"
                                        bg="white"
                                        boxShadow="md"
                                        _dark={{ borderColor: "gray.500", boxShadow: "0 0 0 1px var(--chakra-colors-gray-500), 0 8px 24px rgba(0, 0, 0, 0.5)" }}
                                    >
                                        <iframe
                                            title={t("editor.template.previewTitle")}
                                            src={previewBlobUrl}
                                            style={{ width: "100%", height: "600px", border: "none", display: "block" }}
                                        />
                                    </Box>
                                )}

                                <Button
                                    colorPalette="brand"
                                    alignSelf="flex-start"
                                    onClick={handleFinalize}
                                    loading={finalizeMutation.isPending}
                                    loadingText={t("editor.template.compilingPdf")}
                                    disabled={!selectedTemplateId}
                                    {...BRAND_SOLID_HOVER_PROPS}
                                >
                                    {t("editor.template.use")}
                                </Button>
                            </Stack>
                        )}
                    </Card>
                )}

                {isApproved && documentQuery.isError && (
                    <Card p={6}>
                        <FormAlert status="error">{t("editor.final.documentLoadError")}</FormAlert>
                    </Card>
                )}

                {isApproved && documentQuery.data && (
                    <Card p={6}>
                        <Heading as="h3" size="sm" mb={2}>
                            {t("editor.final.heading")}
                        </Heading>
                        <HStack mb={4}>
                            <Button asChild size="sm" {...SECONDARY_BUTTON_PROPS}>
                                <a href={resumeDocumentDownloadUrl(draftId, settings.apiBaseUrl)} target="_blank" rel="noreferrer">
                                    {t("editor.final.download")}
                                </a>
                            </Button>
                        </HStack>

                        <Heading as="h4" size="xs" mb={3}>
                            {t("editor.final.saveHeading")}
                        </Heading>
                        <Stack as="form" onSubmit={handleSaveApplication} gap={4} maxW="sm">
                            <Input
                                placeholder={t("editor.final.companyPlaceholder")}
                                value={companyName}
                                onChange={(e) => setCompanyName(e.target.value)}
                                required
                            />
                            <HStack>
                                <Input
                                    type="date"
                                    value={applicationDate}
                                    onChange={(e) => setApplicationDate(e.target.value)}
                                    required
                                />
                                <Input
                                    type="time"
                                    value={applicationTime}
                                    onChange={(e) => setApplicationTime(e.target.value)}
                                />
                            </HStack>
                            <NativeSelect.Root>
                                <NativeSelect.Field
                                    value={applicationStatus}
                                    onChange={(e) => setApplicationStatus(e.target.value)}
                                >
                                    {APPLICATION_STATUS_OPTIONS.map((s) => (
                                        <option key={s} value={s}>
                                            {tCommon(`status.${s}`)}
                                        </option>
                                    ))}
                                </NativeSelect.Field>
                                <NativeSelect.Indicator />
                            </NativeSelect.Root>
                            {createApplicationMutation.isError && (
                                <FormAlert status="error">{createApplicationMutation.error.message}</FormAlert>
                            )}
                            <Button
                                type="submit"
                                colorPalette="brand"
                                alignSelf="flex-start"
                                loading={createApplicationMutation.isPending}
                                disabled={!companyName.trim()}
                                {...BRAND_SOLID_HOVER_PROPS}
                            >
                                {t("editor.final.save")}
                            </Button>
                        </Stack>
                    </Card>
                )}
            </Stack>
        </PageContainer>
    );
};

export default ResumeEditorPage;
