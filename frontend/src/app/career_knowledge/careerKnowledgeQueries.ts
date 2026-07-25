import { useQuery } from "@tanstack/react-query";
import axios from "axios";

import { getMyCareerKnowledgeBaseApi, type CareerKnowledgeBaseRead } from "../api/career_knowledge_api";

export const CAREER_KNOWLEDGE_QUERY_KEY = ["career-knowledge"] as const;

export function useCareerKnowledgeBaseQuery() {
    return useQuery<CareerKnowledgeBaseRead | null>({
        queryKey: CAREER_KNOWLEDGE_QUERY_KEY,
        queryFn: async () => {
            try {
                return (await getMyCareerKnowledgeBaseApi()).data;
            } catch (error) {
                // No knowledge base yet is an expected state before the
                // user's first POST, not a fetch failure — surfaced as
                // `data: null` rather than `isError`, so the page shows the
                // "get started" form instead of an error banner.
                if (axios.isAxiosError(error) && error.response?.status === 404) {
                    return null;
                }
                throw error;
            }
        },
    });
}
