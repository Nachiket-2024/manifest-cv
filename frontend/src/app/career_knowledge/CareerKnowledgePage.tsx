import React, { useState } from "react";
import { BookOpen, FileText } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button, Card, ConfirmDialog, FormAlert, LoadingState, PageContainer, Textarea, toaster } from "../sdk";
import { useUnsavedChangesWarning } from "../app_sdk";
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
                icon={BookOpen}
            >
                <LoadingState message={t("loading")} />
            </PageContainer>
        );
    }

    return (
        <PageContainer
            title={t("title")}
            description={t("fullDescription")}
            icon={BookOpen}
        >
            <div className="max-w-5xl space-y-6">
                {isError && <FormAlert status="error">{t("loadError")}</FormAlert>}

                {!knowledgeBase ? (
                    <Card className="border-t-[3px] border-t-brand-solid p-5 md:p-7">
                        <div className="mb-2 flex items-start gap-3">
                            <FileText size={20} className="mt-0.5 text-brand-solid" aria-hidden="true" />
                            <h2 className="text-lg font-semibold text-fg-default">{t("getStarted.heading")}</h2>
                        </div>
                        <p className="mb-5 max-w-3xl text-sm leading-6 text-fg-muted">
                            {t("getStarted.body")}
                        </p>
                        <form className="space-y-4" onSubmit={handleCreate}>
                            <Textarea
                                className="min-h-[24rem] font-mono text-sm leading-6"
                                value={rawInput}
                                onChange={(e) => setRawInput(e.target.value)}
                                placeholder={t("getStarted.placeholder")}
                            />
                            {createMutation.isError && (
                                <FormAlert status="error">{createMutation.error.message}</FormAlert>
                            )}
                            <Button
                                type="submit"
                                variant="brand"
                                className="self-start"
                                loading={createMutation.isPending}
                                disabled={!rawInput.trim()}
                            >
                                {t("getStarted.submit")}
                            </Button>
                        </form>
                    </Card>
                ) : (
                    <Card className="border-t-[3px] border-t-brand-solid p-5 md:p-7">
                        <div className="mb-2 flex items-start gap-3">
                            <FileText size={20} className="mt-0.5 text-brand-solid" aria-hidden="true" />
                            <h2 className="text-lg font-semibold text-fg-default">{t("existing.heading")}</h2>
                        </div>
                        <p className="mb-5 max-w-3xl text-sm leading-6 text-fg-muted">
                            {t("existing.body")}
                        </p>
                        <form className="space-y-4" onSubmit={handleSave}>
                            <Textarea
                                className="min-h-[30rem] font-mono text-sm leading-6"
                                value={content}
                                onChange={(e) => setContent(e.target.value)}
                            />
                            {updateMutation.isError && (
                                <FormAlert status="error">{updateMutation.error.message}</FormAlert>
                            )}
                            <div className="flex flex-wrap gap-3">
                                <Button
                                    type="submit"
                                    variant="brand"
                                    loading={updateMutation.isPending}
                                    disabled={!isDirty || !content.trim()}
                                >
                                    {t("existing.save")}
                                </Button>
                                <Button
                                    variant="destructive-outline"
                                    onClick={() => setDeleteConfirmOpen(true)}
                                >
                                    {t("existing.startOver")}
                                </Button>
                            </div>
                        </form>

                        <div className="mt-6 border-t border-border-card pt-4">
                            <Button
                                size="sm"
                                variant="outline"
                                className="self-start"
                                onClick={() => setShowOriginalInput((v) => !v)}
                            >
                                {showOriginalInput ? t("existing.hideOriginal") : t("existing.showOriginal")}
                            </Button>
                            {showOriginalInput && (
                                <pre className="mt-3 whitespace-pre-wrap rounded-md border border-border-card bg-bg-muted p-4 font-mono text-sm leading-6 text-fg-muted">
                                    {knowledgeBase.raw_input}
                                </pre>
                            )}
                        </div>
                    </Card>
                )}
            </div>

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
