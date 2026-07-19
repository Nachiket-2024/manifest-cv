// tests/frontend/integration/login_page.test.tsx
//
// Regression coverage for a bug where LoginPage gated its *entire* render
// (including the plain email/password LoginForm) behind a shared OAuth2
// loading flag that flipped true/false on every session-check request,
// including ones triggered internally by a normal password login — so
// submitting ordinary credentials made this page briefly unmount LoginForm
// for a full-page "Signing you in..." spinner while the internal profile
// fetch was in flight, then remount a fresh LoginForm afterwards. These
// tests pin that the login form stays mounted and interactive throughout a
// login attempt.
import type { ReactElement } from 'react';
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ChakraProvider, defaultSystem } from '@chakra-ui/react';
import { MemoryRouter } from 'react-router-dom';
import MockAdapter from 'axios-mock-adapter';

import api from '@/api/axiosInstance';
import { useAuthStore } from '@/store/authStore';
import LoginPage from '@/auth/login/LoginPage';

const mock = new MockAdapter(api);
const initialAuthState = useAuthStore.getState();

function renderWithProviders(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ChakraProvider value={defaultSystem}>
        <MemoryRouter>{ui}</MemoryRouter>
      </ChakraProvider>
    </QueryClientProvider>
  );
}

function delayed<T>(value: [number, T], ms: number) {
  return () => new Promise<[number, T]>((resolve) => setTimeout(() => resolve(value), ms));
}

describe('LoginPage stays on the login form throughout a login attempt', () => {
  beforeEach(() => {
    mock.reset();
    useAuthStore.setState(initialAuthState, true);
  });

  it('does not unmount LoginForm while the post-login profile fetch is in flight', async () => {
    mock.onPost('/auth/login').reply(200, { message: 'Login successful' });
    // Deliberately slow so the test can observe the in-flight state — this
    // is the GET /auth/me round-trip useLoginMutation triggers internally.
    mock
      .onGet('/auth/me')
      .reply(delayed([200, { name: 'Test User', email: 'user@example.com', role: 'user', permissions: [] }], 100));

    renderWithProviders(<LoginPage />);

    await userEvent.type(screen.getByPlaceholderText('Email'), 'user@example.com');
    await userEvent.type(screen.getByPlaceholderText('Password'), 'StrongPass123!');
    await userEvent.click(screen.getByRole('button', { name: 'Login' }));

    // Mid-flight: the login form's own inputs must still be in the DOM —
    // the bug replaced them with a full-page spinner at this exact point.
    expect(screen.getByPlaceholderText('Email')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Password')).toBeInTheDocument();
    expect(screen.queryByText('Signing you in...')).toBeNull();

    await waitFor(() => {
      expect(useAuthStore.getState().isAuthenticated).toBe(true);
    });
  });

  it('keeps whatever the user typed on screen if login ultimately fails', async () => {
    mock.onPost('/auth/login').reply(200, { message: 'Login successful' });
    // useLoginMutation treats a non-200 /auth/me after a "successful" login
    // POST as a failure of the whole mutation (see useLoginMutation.ts).
    mock.onGet('/auth/me').reply(delayed([401, { detail: 'Not authenticated' }], 50));

    renderWithProviders(<LoginPage />);

    const emailInput = screen.getByPlaceholderText('Email') as HTMLInputElement;
    await userEvent.type(emailInput, 'user@example.com');
    await userEvent.type(screen.getByPlaceholderText('Password'), 'StrongPass123!');
    await userEvent.click(screen.getByRole('button', { name: 'Login' }));

    await waitFor(() => {
      // extractApiErrorMessage now surfaces FastAPI's real `detail` message
      // (see api/apiError.ts) rather than falling back to a generic
      // "Login failed" — this mock's 401 body is exactly what a real
      // GET /auth/me 401 looks like in production.
      expect(screen.queryByText(/not authenticated|failed|invalid|error/i)).toBeInTheDocument();
    });

    // The bug this guards against: the whole page swapping to a full-page
    // spinner and back unmounts LoginForm, resetting its local email/password
    // state to empty strings even though the user never cleared the form.
    expect((screen.getByPlaceholderText('Email') as HTMLInputElement).value).toBe(
      'user@example.com'
    );
  });
});
