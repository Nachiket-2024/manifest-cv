import React, { useState } from "react";
import { Button, Heading, Stack, Text, Textarea } from "@chakra-ui/react";
import { useTranslation } from "react-i18next";

import {
    PageContainer,
    Card,
    LoadingState,
    FormAlert,
    ConfirmDialog,
    toaster,
    useUnsavedChangesWarning,
    BRAND_SOLID_HOVER_PROPS,
    SECONDARY_BUTTON_PROPS,
} from "../app_sdk";
import { DESTRUCTIVE_OUTLINE_HOVER_PROPS } from "../ui/buttonStyles";
import { useCareerKnowledgeBaseQuery } from "./careerKnowledgeQueries";
import {
    useCreateCareerKnowledgeBaseMutation,
    useUpdateCareerKnowledgeBaseMutation,
    useDeleteCareerKnowledgeBaseMutation,
} from "./careerKnowledgeMutations";

/**
 * CareerKnowledgePage
 * ----------------------------
 * The caller's single career knowledge base (backend: /career-knowledge).
 * A user with no knowledge base yet sees a "get started" text dump form;
 * submitting it calls Gemini server-side to reorganize the raw dump into
 * structured Markdown before returning it. The create request briefly
 * takes a few seconds for that reason. Once a knowledge base exists, the
 * structured content is directly editable. The original raw text stays
 * visible (collapsed) alongside it so the user can always verify nothing
 * was added that they didn't write themselves.
 */
const CareerKnowledgePage: React.FC = () => {
    const { t } = useTranslation("career_knowledge");
    const { data: knowledgeBase, isLoading, isError } = useCareerKnowledgeBaseQuery();

    const createMutation = useCreateCareerKnowledgeBaseMutation();
    const updateMutation = useUpdateCareerKnowledgeBaseMutation();
    const deleteMutation = useDeleteCareerKnowledgeBaseMutation();

    const [rawInput, setRawInput] = useState("");
    const [content, setContent] = useState("");
    const [prevKnowledgeContent, setPrevKnowledgeContent] = useState<string | undefined>(undefined);
    const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
    const [showOriginalInput, setShowOriginalInput] = useState(false);

    // Sync local editable state whenever the server's copy changes (initial
    // load, or right after a save) so the textarea always starts from what's
    // actually persisted.
    if (knowledgeBase && knowledgeBase.content !== prevKnowledgeContent) {
        setPrevKnowledgeContent(knowledgeBase.content);
        setContent(knowledgeBase.content);
    }

    const isDirty = knowledgeBase ? content !== knowledgeBase.content : rawInput.length > 0;
    useUnsavedChangesWarning(isDirty);

    const handleCreate = (e: React.FormEvent) => {
        e.preventDefault();
        createMutation.mutate(
            { raw_input: rawInput },
            {
                onSuccess: () => {
                    toaster.create({ title: t("toast.created"), type: "success" });
                    setRawInput("");
                },
            }
        );
    };

    const handleSave = (e: React.FormEvent) => {
        e.preventDefault();
        updateMutation.mutate(
            { content },
            { onSuccess: () => toaster.create({ title: t("toast.saved"), type: "success" }) }
        );
    };

    const handleDeleteConfirm = () => {
        deleteMutation.mutate(undefined, {
            onSuccess: () => {
                toaster.create({ title: t("toast.deleted"), type: "success" });
                setDeleteConfirmOpen(false);
            },
            onError: (error) => {
                toaster.create({ title: error.message, type: "error" });
            },
        });
    };

    if (isLoading) {
        return (
            <PageContainer
                title={t("title")}
                description={t("description")}
            >
                <LoadingState message={t("loading")} />
            </PageContainer>
        );
    }

    return (
        <PageContainer
            title={t("title")}
            description={t("fullDescription")}
        >
            <Stack gap={6} maxW="3xl">
                {isError && <FormAlert status="error">{t("loadError")}</FormAlert>}

                {!knowledgeBase ? (
                    <Card p={6}>
                        <Heading as="h2" size="md" mb={2}>
                            {t("getStarted.heading")}
                        </Heading>
                        <Text color="fg.muted" mb={4}>
                            {t("getStarted.body")}
                        </Text>
                        <Stack as="form" onSubmit={handleCreate} gap={4}>
                            <Textarea
                                value={rawInput}
                                onChange={(e) => setRawInput(e.target.value)}
                                placeholder={t("getStarted.placeholder")}
                                rows={16}
                            />
                            {createMutation.isError && (
                                <FormAlert status="error">{createMutation.error.message}</FormAlert>
                            )}
                            <Button
                                type="submit"
                                colorPalette="brand"
                                alignSelf="flex-start"
                                loading={createMutation.isPending}
                                loadingText={t("getStarted.submitLoading")}
                                disabled={!rawInput.trim()}
                                {...BRAND_SOLID_HOVER_PROPS}
                            >
                                {t("getStarted.submit")}
                            </Button>
                        </Stack>
                    </Card>
                ) : (
                    <Card p={6}>
                        <Heading as="h2" size="md" mb={2}>
                            {t("existing.heading")}
                        </Heading>
                        <Text color="fg.muted" mb={4}>
                            {t("existing.body")}
                        </Text>
                        <Stack as="form" onSubmit={handleSave} gap={4}>
                            <Textarea
                                value={content}
                                onChange={(e) => setContent(e.target.value)}
                                rows={20}
                                fontFamily="mono"
                            />
                            {updateMutation.isError && (
                                <FormAlert status="error">{updateMutation.error.message}</FormAlert>
                            )}
                            <Stack direction="row" gap={3}>
                                <Button
                                    type="submit"
                                    colorPalette="brand"
                                    loading={updateMutation.isPending}
                                    loadingText={t("existing.saveLoading")}
                                    disabled={!isDirty || !content.trim()}
                                    {...BRAND_SOLID_HOVER_PROPS}
                                >
                                    {t("existing.save")}
                                </Button>
                                <Button
                                    variant="outline"
                                    colorPalette="red"
                                    onClick={() => setDeleteConfirmOpen(true)}
                                    {...DESTRUCTIVE_OUTLINE_HOVER_PROPS}
                                >
                                    {t("existing.startOver")}
                                </Button>
                            </Stack>
                        </Stack>

                        <Stack gap={2} mt={6} pt={4} borderTopWidth="1px" borderColor="border.default">
                            <Button
                                size="sm"
                                alignSelf="flex-start"
                                onClick={() => setShowOriginalInput((v) => !v)}
                                {...SECONDARY_BUTTON_PROPS}
                            >
                                {showOriginalInput ? t("existing.hideOriginal") : t("existing.showOriginal")}
                            </Button>
                            {showOriginalInput && (
                                <Text color="fg.muted" fontFamily="mono" fontSize="sm" whiteSpace="pre-wrap">
                                    {knowledgeBase.raw_input}
                                </Text>
                            )}
                        </Stack>
                    </Card>
                )}
            </Stack>

            <ConfirmDialog
                isOpen={deleteConfirmOpen}
                title={t("deleteDialog.title")}
                description={t("deleteDialog.description")}
                confirmLabel={t("deleteDialog.confirm")}
                isLoading={deleteMutation.isPending}
                onConfirm={handleDeleteConfirm}
                onCancel={() => setDeleteConfirmOpen(false)}
            />
        </PageContainer>
    );
};

export default CareerKnowledgePage;
