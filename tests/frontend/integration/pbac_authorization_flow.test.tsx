import type { ReactNode } from 'react';
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor, renderHook, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ChakraProvider, defaultSystem } from '@chakra-ui/react';
import MockAdapter from 'axios-mock-adapter';

import api from '@/api/axiosInstance';
import { useAuthStore } from '@/store/authStore';
import { useLoginMutation } from '@/auth/login/useLoginMutation';
import { useAuthSession } from '@/auth/current_user/useCurrentUserQuery';
import { Authorized } from '@/authorization/Authorized';
import { IfCan } from '@/authorization/IfCan';

const mock = new MockAdapter(api);
const PASSWORD = 'StrongPass123!';
const initialAuthState = useAuthStore.getState();

function queryWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

function Dashboard() {
  return (
    <div>
      <Authorized permission="users:list_all" fallback={<div>No admin access</div>}>
        <div>Admin Panel</div>
      </Authorized>
      <IfCan action="documents:view">
        <div>Document Viewer</div>
      </IfCan>
    </div>
  );
}

function renderDashboard() {
  return render(
    <ChakraProvider value={defaultSystem}>
      <Dashboard />
    </ChakraProvider>
  );
}

describe('PBAC end-to-end: login -> permissions loaded -> conditional UI renders correctly', () => {
  beforeEach(() => {
    mock.reset();
    useAuthStore.setState(initialAuthState, true);
  });

  it('shows only the UI gated behind permissions the logged-in user actually holds', async () => {
    mock.onPost('/auth/login').reply(200, { message: 'Login successful' });
    mock.onGet('/auth/me').reply(200, {
      name: 'Test User',
      email: 'user@example.com',
      role: 'user',
      permissions: ['documents:view'], // holds this, NOT users:list_all
    });

    renderDashboard();

    // Before login resolves: authentication status is still unknown, so
    // neither gated element (nor its fallback) has committed to an answer
    // yet — see Authorized/IfCan's own "never show anything prematurely"
    // guarantee.
    expect(screen.queryByText('Admin Panel')).toBeNull();
    expect(screen.queryByText('No admin access')).toBeNull();
    expect(screen.queryByText('Document Viewer')).toBeNull();

    const { result } = renderHook(() => useLoginMutation(), { wrapper: queryWrapper() });
    await act(async () => {
      await result.current.mutateAsync({ email: 'user@example.com', password: PASSWORD });
    });

    await waitFor(() => {
      expect(screen.getByText('Document Viewer')).toBeInTheDocument();
    });
    expect(screen.getByText('No admin access')).toBeInTheDocument();
    expect(screen.queryByText('Admin Panel')).toBeNull();
  });

  it('grants access to admin-gated UI when the user holds that permission too', async () => {
    mock.onPost('/auth/login').reply(200, { message: 'Login successful' });
    mock.onGet('/auth/me').reply(200, {
      name: 'Admin User',
      email: 'admin@example.com',
      role: 'admin',
      permissions: ['documents:view', 'users:list_all'],
    });

    renderDashboard();

    const { result } = renderHook(() => useLoginMutation(), { wrapper: queryWrapper() });
    await act(async () => {
      await result.current.mutateAsync({ email: 'admin@example.com', password: PASSWORD });
    });

    await waitFor(() => {
      expect(screen.getByText('Admin Panel')).toBeInTheDocument();
    });
    expect(screen.getByText('Document Viewer')).toBeInTheDocument();
    expect(screen.queryByText('No admin access')).toBeNull();
  });

  it('a failed login never reveals protected content, regardless of what the session check later resolves to', async () => {
    // useLoginMutation's own mutationFn short-circuits at the credentials
    // step and never reaches the profile fetch, so the auth store's
    // isAuthenticated stays null after this alone — in the real app,
    // App.tsx's own session-sync hook independently resolves it regardless
    // of how login went. Simulating that here via useAuthSession too (also
    // failing, since no session was ever established).
    mock.onPost('/auth/login').reply(401, { detail: 'Invalid credentials' });
    mock.onGet('/auth/me').reply(401, { detail: 'Not authenticated' });

    renderDashboard();

    const { result: loginResult } = renderHook(() => useLoginMutation(), { wrapper: queryWrapper() });
    await act(async () => {
      await result_ignoreRejection(loginResult.current.mutateAsync({ email: 'user@example.com', password: 'wrong-password' }));
    });
    expect(screen.queryByText('Admin Panel')).toBeNull();
    expect(screen.queryByText('Document Viewer')).toBeNull();

    renderHook(() => useAuthSession(), { wrapper: queryWrapper() });

    await waitFor(() => {
      expect(useAuthStore.getState().isAuthenticated).toBe(false);
    });
    // Now definitively resolved to unauthenticated — Authorized's fallback
    // renders (unlike the still-null/loading case), but the protected
    // content itself never does
    expect(screen.getByText('No admin access')).toBeInTheDocument();
    expect(screen.queryByText('Admin Panel')).toBeNull();
    expect(screen.queryByText('Document Viewer')).toBeNull();
  });
});

// mutateAsync rejects on failure — this test intentionally triggers that
// failure and only cares about the resulting auth-store/DOM state, not the
// rejection itself, so swallow it rather than letting it fail the test.
async function result_ignoreRejection(promise: Promise<unknown>): Promise<void> {
  await promise.catch(() => undefined);
}
