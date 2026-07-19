import React, { useState } from "react";
import { Button, Heading, Stack, Text, Textarea } from "@chakra-ui/react";

import PageContainer from "../components/ui/PageContainer";
import Card from "../components/ui/Card";
import LoadingState from "../components/ui/LoadingState";
import FormAlert from "../components/ui/FormAlert";
import ConfirmDialog from "../components/ui/ConfirmDialog";
import { toaster } from "../components/ui/toasterInstance";
import { useUnsavedChangesWarning } from "../hooks/useUnsavedChangesWarning";
import { useCareerKnowledgeBaseQuery } from "./careerKnowledgeQueries";
import {
    useCreateCareerKnowledgeBaseMutation,
    useUpdateCareerKnowledgeBaseMutation,
    useDeleteCareerKnowledgeBaseMutation,
} from "./careerKnowledgeMutations";

/**
 * CareerKnowledgePage
 * ----------------------------
 * The caller's single career knowledge base (backend: /career-knowledge) —
 * claude.md's "Application Flow" steps 1-5. A user with no knowledge base
 * yet sees a "get started" text dump form (step 1); submitting it calls
 * Gemini server-side to reorganize the raw dump into structured Markdown
 * (steps 2-4, Phase 1.5) before returning it — the create request briefly
 * takes a few seconds for that reason. Once a knowledge base exists, the
 * structured content is directly editable (step 5); the original raw text
 * stays visible (collapsed) alongside it so the user can always verify
 * nothing was added that they didn't write themselves.
 */
const CareerKnowledgePage: React.FC = () => {
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
                    toaster.create({ title: "Knowledge base created", type: "success" });
                    setRawInput("");
                },
            }
        );
    };

    const handleSave = (e: React.FormEvent) => {
        e.preventDefault();
        updateMutation.mutate(
            { content },
            { onSuccess: () => toaster.create({ title: "Knowledge base saved", type: "success" }) }
        );
    };

    const handleDeleteConfirm = () => {
        deleteMutation.mutate(undefined, {
            onSuccess: () => {
                toaster.create({ title: "Knowledge base deleted", type: "success" });
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
                title="Career Knowledge"
                description="Your private source material for tailored resumes."
            >
                <LoadingState message="Loading your knowledge base..." />
            </PageContainer>
        );
    }

    return (
        <PageContainer
            title="Career Knowledge"
            description="Your private source material — resume text, LinkedIn, projects, skills, achievements, and notes. Resume generation draws only from what's here."
        >
            <Stack gap={6} maxW="3xl">
                {isError && <FormAlert status="error">Failed to load your knowledge base</FormAlert>}

                {!knowledgeBase ? (
                    <Card p={6}>
                        <Heading as="h2" size="md" mb={2}>
                            Get started
                        </Heading>
                        <Text color="fg.muted" mb={4}>
                            Paste everything you have — resume text, LinkedIn profile, GitHub projects, work
                            experience, achievements, skills, and notes. This becomes your single source of truth;
                            nothing beyond what you write here is ever added on your behalf.
                        </Text>
                        <Stack as="form" onSubmit={handleCreate} gap={4}>
                            <Textarea
                                value={rawInput}
                                onChange={(e) => setRawInput(e.target.value)}
                                placeholder="Paste your resume, LinkedIn text, projects, experience, skills, achievements, notes..."
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
                                loadingText="Structuring with AI..."
                                disabled={!rawInput.trim()}
                            >
                                Create knowledge base
                            </Button>
                        </Stack>
                    </Card>
                ) : (
                    <Card p={6}>
                        <Heading as="h2" size="md" mb={2}>
                            Your knowledge base
                        </Heading>
                        <Text color="fg.muted" mb={4}>
                            Structured by AI from what you pasted in, and directly editable any time. Tailored
                            resumes are generated only from what's written here — nothing is ever added that
                            wasn't in your original text.
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
                                    loadingText="Saving..."
                                    disabled={!isDirty || !content.trim()}
                                >
                                    Save changes
                                </Button>
                                <Button variant="outline" colorPalette="red" onClick={() => setDeleteConfirmOpen(true)}>
                                    Start over
                                </Button>
                            </Stack>
                        </Stack>

                        <Stack gap={2} mt={6} pt={4} borderTopWidth="1px" borderColor="border.default">
                            <Button
                                variant="ghost"
                                size="sm"
                                alignSelf="flex-start"
                                onClick={() => setShowOriginalInput((v) => !v)}
                            >
                                {showOriginalInput ? "Hide" : "Show"} original text you pasted in
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
                title="Delete knowledge base"
                description="This permanently deletes your career knowledge base. You'll need to paste your information again to rebuild it."
                confirmLabel="Delete"
                isLoading={deleteMutation.isPending}
                onConfirm={handleDeleteConfirm}
                onCancel={() => setDeleteConfirmOpen(false)}
            />
        </PageContainer>
    );
};

export default CareerKnowledgePage;
