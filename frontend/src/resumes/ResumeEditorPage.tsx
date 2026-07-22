import React, { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
    Badge,
    Button,
    Heading,
    HStack,
    Input,
    NativeSelect,
    Stack,
    Text,
    Textarea,
} from "@chakra-ui/react";

import PageContainer from "../ui/PageContainer";
import Card from "../ui/Card";
import LoadingState from "../ui/LoadingState";
import FormAlert from "../ui/FormAlert";
import { toaster } from "../ui/toasterInstance";
import { useUnsavedChangesWarning } from "../profile/useUnsavedChangesWarning";
import { settings } from "../sdk";

import { useResumeDraftQuery, useResumeTemplatesQuery, useFinalizedResumeDocumentQuery } from "./resumeQueries";
import {
    useUpdateResumeDraftMutation,
    useApproveResumeDraftMutation,
    useFinalizeResumeDocumentMutation,
} from "./resumeMutations";
import { resumeTemplatePreviewUrl, resumeDocumentDownloadUrl } from "../api/document_api";
import { useCreateApplicationMutation } from "../applications/applicationMutations";

const APPLICATION_STATUS_OPTIONS = ["applied", "interviewing", "offered", "rejected"] as const;

/**
 * ResumeEditorPage
 * ----------------------------
 * One resume draft's full lifecycle (claude.md flow steps 9-23): direct
 * content edits or AI-driven refinement while in "draft" status, then
 * approval (locking content), then Phase 3's template preview →
 * finalize-to-PDF → save-as-tracked-application, all against the one
 * draft identified by the :draftId route param.
 */
const ResumeEditorPage: React.FC = () => {
    const { draftId: draftIdParam } = useParams<{ draftId: string }>();
    const draftId = Number(draftIdParam);
    const navigate = useNavigate();

    const { data: draft, isLoading, isError } = useResumeDraftQuery(draftId);
    const updateMutation = useUpdateResumeDraftMutation(draftId);
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
    const [companyName, setCompanyName] = useState("");
    const [applicationDate, setApplicationDate] = useState(() => new Date().toISOString().slice(0, 10));
    const [applicationTime, setApplicationTime] = useState("");
    const [applicationStatus, setApplicationStatus] = useState<string>("applied");

    const handleSave = (e: React.FormEvent) => {
        e.preventDefault();
        updateMutation.mutate(
            { content },
            { onSuccess: () => toaster.create({ title: "Resume saved", type: "success" }) }
        );
    };

    const handleRefine = (e: React.FormEvent) => {
        e.preventDefault();
        updateMutation.mutate(
            { refinement_prompt: refinementPrompt },
            {
                onSuccess: () => {
                    toaster.create({ title: "Resume updated", type: "success" });
                    setRefinementPrompt("");
                },
            }
        );
    };

    const handleApprove = () => {
        approveMutation.mutate(undefined, {
            onSuccess: () => toaster.create({ title: "Resume approved — content is now locked", type: "success" }),
            onError: (error) => toaster.create({ title: error.message, type: "error" }),
        });
    };

    const handleFinalize = () => {
        if (!selectedTemplateId) return;
        finalizeMutation.mutate(selectedTemplateId, {
            onSuccess: () => toaster.create({ title: "PDF generated", type: "success" }),
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
                    toaster.create({ title: "Application saved", type: "success" });
                    navigate("/applications");
                },
                onError: (error) => toaster.create({ title: error.message, type: "error" }),
            }
        );
    };

    if (isLoading) {
        return (
            <PageContainer title="Resume">
                <LoadingState message="Loading resume..." />
            </PageContainer>
        );
    }

    if (isError || !draft) {
        return (
            <PageContainer title="Resume">
                <FormAlert status="error">Failed to load this resume</FormAlert>
            </PageContainer>
        );
    }

    return (
        <PageContainer
            title="Resume"
            description="Tailored from your knowledge base — nothing beyond what's already written there is ever added."
            actions={
                <Badge colorPalette={isApproved ? "green" : "yellow"} textTransform="capitalize" fontSize="sm">
                    {draft.status}
                </Badge>
            }
        >
            <Stack gap={6} maxW="3xl">
                <Card p={6}>
                    <Heading as="h3" size="sm" mb={2}>
                        Job description
                    </Heading>
                    <Text color="fg.muted" whiteSpace="pre-wrap" fontSize="sm">
                        {draft.job_description}
                    </Text>
                </Card>

                <Card p={6}>
                    <Heading as="h3" size="sm" mb={4}>
                        Resume content
                    </Heading>
                    <Stack as="form" onSubmit={handleSave} gap={4}>
                        <Textarea
                            value={content}
                            onChange={(e) => setContent(e.target.value)}
                            rows={20}
                            fontFamily="mono"
                            disabled={isApproved || updateMutation.isPending}
                        />
                        {updateMutation.isError && <FormAlert status="error">{updateMutation.error.message}</FormAlert>}
                        {!isApproved && (
                            <Button
                                type="submit"
                                colorPalette="brand"
                                alignSelf="flex-start"
                                loading={updateMutation.isPending}
                                disabled={!isDirty || !content.trim()}
                            >
                                Save changes
                            </Button>
                        )}
                    </Stack>
                </Card>

                {!isApproved && (
                    <Card p={6}>
                        <Heading as="h3" size="sm" mb={2}>
                            Ask for a change
                        </Heading>
                        <Text color="fg.muted" mb={4} fontSize="sm">
                            Tell the AI how to adjust this resume — e.g. "emphasize my backend experience" or
                            "use the project section instead of the internship". It only rearranges what's
                            already in your knowledge base.
                        </Text>
                        <Stack as="form" onSubmit={handleRefine} gap={4}>
                            <Textarea
                                value={refinementPrompt}
                                onChange={(e) => setRefinementPrompt(e.target.value)}
                                placeholder="Describe the change you want..."
                                rows={3}
                            />
                            <HStack>
                                <Button
                                    type="submit"
                                    variant="outline"
                                    loading={updateMutation.isPending}
                                    loadingText="Refining..."
                                    disabled={!refinementPrompt.trim()}
                                >
                                    Refine with AI
                                </Button>
                                <Button
                                    colorPalette="brand"
                                    onClick={handleApprove}
                                    loading={approveMutation.isPending}
                                    disabled={!content.trim() || isDirty}
                                    title={isDirty ? "Save your changes before approving" : undefined}
                                >
                                    Approve resume
                                </Button>
                            </HStack>
                        </Stack>
                    </Card>
                )}

                {isApproved && (
                    <Card p={6}>
                        <Heading as="h3" size="sm" mb={2}>
                            Choose a template
                        </Heading>
                        <Text color="fg.muted" mb={4} fontSize="sm">
                            Content is locked now that this resume is approved — only presentation changes from here.
                        </Text>

                        {templatesQuery.isLoading && <LoadingState message="Loading templates..." />}

                        {templatesQuery.isError && (
                            <FormAlert status="error">Failed to load templates — try reloading the page</FormAlert>
                        )}

                        {templatesQuery.data && (
                            <Stack gap={4}>
                                <NativeSelect.Root w="200px">
                                    <NativeSelect.Field
                                        value={selectedTemplateId ?? ""}
                                        onChange={(e) => setSelectedTemplateOverride(e.target.value)}
                                    >
                                        {templatesQuery.data.map((t) => (
                                            <option key={t.id} value={t.id}>
                                                {t.label}
                                            </option>
                                        ))}
                                    </NativeSelect.Field>
                                    <NativeSelect.Indicator />
                                </NativeSelect.Root>

                                {selectedTemplateId && (
                                    <iframe
                                        title="Resume preview"
                                        src={resumeTemplatePreviewUrl(draftId, selectedTemplateId, settings.apiBaseUrl)}
                                        style={{ width: "100%", height: "600px", border: "1px solid var(--chakra-colors-border-default)" }}
                                    />
                                )}

                                <Button
                                    colorPalette="brand"
                                    alignSelf="flex-start"
                                    onClick={handleFinalize}
                                    loading={finalizeMutation.isPending}
                                    loadingText="Compiling PDF..."
                                    disabled={!selectedTemplateId}
                                >
                                    Use this template
                                </Button>
                            </Stack>
                        )}
                    </Card>
                )}

                {isApproved && documentQuery.isError && (
                    <Card p={6}>
                        <FormAlert status="error">Failed to check for a finalized PDF — try reloading the page</FormAlert>
                    </Card>
                )}

                {isApproved && documentQuery.data && (
                    <Card p={6}>
                        <Heading as="h3" size="sm" mb={2}>
                            Final resume ready
                        </Heading>
                        <HStack mb={4}>
                            <Button asChild variant="outline" size="sm">
                                <a href={resumeDocumentDownloadUrl(draftId, settings.apiBaseUrl)} target="_blank" rel="noreferrer">
                                    Download PDF
                                </a>
                            </Button>
                        </HStack>

                        <Heading as="h4" size="xs" mb={3}>
                            Save this application
                        </Heading>
                        <Stack as="form" onSubmit={handleSaveApplication} gap={4} maxW="sm">
                            <Input
                                placeholder="Company name"
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
                                            {s}
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
                            >
                                Save application
                            </Button>
                        </Stack>
                    </Card>
                )}
            </Stack>
        </PageContainer>
    );
};

export default ResumeEditorPage;
