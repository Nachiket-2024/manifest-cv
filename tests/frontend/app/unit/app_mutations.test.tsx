import { describe, expect, it, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import MockAdapter from "axios-mock-adapter";
import type { ReactNode } from "react";

import api from "@/api/axiosInstance";
import { queryClient } from "@app/sdk";
import {
    useCreateApplicationMutation,
    useDeleteApplicationMutation,
} from "@app/applications/applicationMutations";

const mock = new MockAdapter(api);

function wrapper() {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
    return ({ children }: { children: ReactNode }) => (
        <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
}

describe("downstream mutation hooks", () => {
    beforeEach(() => {
        mock.reset();
        queryClient.clear();
    });

    it("creates an application and updates its detail cache", async () => {
        const application = { id: 7, company_name: "Acme", status: "applied" };
        mock.onPost("/applications/").reply(201, application);
        const { result } = renderHook(() => useCreateApplicationMutation(), { wrapper: wrapper() });

        let created: typeof application | undefined;
        await act(async () => {
            created = await result.current.mutateAsync({
                workspace_id: 3,
                company_name: "Acme",
                application_date: "2026-01-01",
                status: "applied",
            });
        });

        expect(created).toEqual(application);
        await waitFor(() => expect(queryClient.getQueryData(["applications", 7])).toEqual(application));
    });

    it("surfaces the API error when application deletion fails", async () => {
        mock.onDelete("/applications/7").reply(409, { detail: "Application is locked" });
        const { result } = renderHook(() => useDeleteApplicationMutation(), { wrapper: wrapper() });

        await act(async () => {
            await expect(result.current.mutateAsync(7)).rejects.toThrow("Application is locked");
        });

        await waitFor(() => expect(result.current.isError).toBe(true));
    });

});
