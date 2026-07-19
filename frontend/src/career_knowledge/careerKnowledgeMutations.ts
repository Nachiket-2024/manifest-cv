import { useMutation } from "@tanstack/react-query";

import {
    createCareerKnowledgeBaseApi,
    updateCareerKnowledgeBaseApi,
    deleteCareerKnowledgeBaseApi,
    type CareerKnowledgeBaseCreatePayload,
    type CareerKnowledgeBaseUpdatePayload,
    type CareerKnowledgeBaseRead,
} from "../api/career_knowledge_api";
import { extractApiErrorMessage } from "../api/apiError";
import { queryClient } from "../store/queryClient";
import { CAREER_KNOWLEDGE_QUERY_KEY } from "./careerKnowledgeQueries";

export function useCreateCareerKnowledgeBaseMutation() {
    return useMutation<CareerKnowledgeBaseRead, Error, CareerKnowledgeBaseCreatePayload>({
        mutationFn: async (payload) => {
            try {
                return (await createCareerKnowledgeBaseApi(payload)).data;
            } catch (error) {
                throw new Error(extractApiErrorMessage(error, "Failed to create knowledge base"), { cause: error });
            }
        },
        onSuccess: (data) => {
            queryClient.setQueryData(CAREER_KNOWLEDGE_QUERY_KEY, data);
        },
    });
}

export function useUpdateCareerKnowledgeBaseMutation() {
    return useMutation<CareerKnowledgeBaseRead, Error, CareerKnowledgeBaseUpdatePayload>({
        mutationFn: async (payload) => {
            try {
                return (await updateCareerKnowledgeBaseApi(payload)).data;
            } catch (error) {
                throw new Error(extractApiErrorMessage(error, "Failed to save knowledge base"), { cause: error });
            }
        },
        onSuccess: (data) => {
            queryClient.setQueryData(CAREER_KNOWLEDGE_QUERY_KEY, data);
        },
    });
}

export function useDeleteCareerKnowledgeBaseMutation() {
    return useMutation<void, Error, void>({
        mutationFn: async () => {
            try {
                await deleteCareerKnowledgeBaseApi();
            } catch (error) {
                throw new Error(extractApiErrorMessage(error, "Failed to delete knowledge base"), { cause: error });
            }
        },
        onSuccess: () => {
            queryClient.setQueryData(CAREER_KNOWLEDGE_QUERY_KEY, null);
        },
    });
}
