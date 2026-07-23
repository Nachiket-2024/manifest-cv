// tests/frontend/integration/password_policy_consistency.test.tsx
//
// Regression coverage for a frontend/backend password-policy mismatch:
// SignupForm and PasswordResetConfirmForm both required a special character
// but never checked for a lowercase letter, while the backend
// (password_service.validate_password_strength) requires length>=8 + upper +
// lower + digit and has no special-character requirement at all. A password
// like "PASSWORD1!" passed every client-side check (shown as "Strong") and
// then got rejected by the backend for missing a lowercase letter — a
// confusing UX bug from two validation layers enforcing different rules.
// These tests pin the two layers back in sync.
import type { ReactElement } from 'react';
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ChakraProvider, defaultSystem } from '@chakra-ui/react';
import { MemoryRouter } from 'react-router-dom';
import MockAdapter from 'axios-mock-adapter';

import api from '@/mystic_auth/api/axiosInstance';
import SignupForm from '@/mystic_auth/auth/signup/SignupForm';
import PasswordResetConfirmForm from '@/mystic_auth/auth/password_reset_confirm/PasswordResetConfirmForm';

const mock = new MockAdapter(api);

function renderWithProviders(ui: ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <ChakraProvider value={defaultSystem}>
        <MemoryRouter>{ui}</MemoryRouter>
      </ChakraProvider>
    </QueryClientProvider>
  );
}

describe('SignupForm password policy matches the backend', () => {
  beforeEach(() => {
    mock.reset();
  });

  it('rejects a password with upper+digit+special but no lowercase, and never calls the API', async () => {
    mock.onPost('/auth/signup').reply(200, { message: 'ok' });
    renderWithProviders(<SignupForm />);

    await userEvent.type(screen.getByPlaceholderText('Enter your name'), 'Test User');
    await userEvent.type(screen.getByPlaceholderText('Enter your email'), 'test@example.com');
    await userEvent.type(screen.getByPlaceholderText('Enter password'), 'PASSWORD1!');
    await userEvent.type(screen.getByPlaceholderText('Confirm password'), 'PASSWORD1!');
    await userEvent.click(screen.getByRole('button', { name: 'Signup' }));

    // Typing into 4 fields plus the async validation pass is occasionally
    // slower than the 5s default under full-suite parallel load (passes
    // reliably in isolation) — give it more headroom rather than flaking.
    expect(
      await screen.findByText('Password must contain at least one lowercase letter', {}, { timeout: 10000 })
    ).toBeInTheDocument();
    expect(mock.history.post.filter((r) => r.url === '/auth/signup')).toHaveLength(0);
  }, 15000);

  it('accepts a password with upper+lower+digit even without a special character', async () => {
    mock.onPost('/auth/signup').reply(200, { message: 'ok' });
    renderWithProviders(<SignupForm />);

    await userEvent.type(screen.getByPlaceholderText('Enter your name'), 'Test User');
    await userEvent.type(screen.getByPlaceholderText('Enter your email'), 'test@example.com');
    await userEvent.type(screen.getByPlaceholderText('Enter password'), 'Password1');
    await userEvent.type(screen.getByPlaceholderText('Confirm password'), 'Password1');
    await userEvent.click(screen.getByRole('button', { name: 'Signup' }));

    await screen.findByText('ok');
    expect(mock.history.post.filter((r) => r.url === '/auth/signup')).toHaveLength(1);
  });
});

describe('PasswordResetConfirmForm password policy matches the backend', () => {
  beforeEach(() => {
    mock.reset();
  });

  it('rejects a password with upper+digit+special but no lowercase, and never calls the API', async () => {
    mock.onPost('/auth/password-reset/confirm').reply(200, { message: 'Password has been reset successfully' });
    renderWithProviders(<PasswordResetConfirmForm token="reset-token-abc" />);

    await userEvent.type(screen.getByPlaceholderText('New Password'), 'PASSWORD1!');
    await userEvent.type(screen.getByPlaceholderText('Confirm New Password'), 'PASSWORD1!');
    await userEvent.click(screen.getByRole('button', { name: 'Reset Password' }));

    expect(
      await screen.findByText('Password must contain at least one lowercase letter')
    ).toBeInTheDocument();
    expect(mock.history.post.filter((r) => r.url === '/auth/password-reset/confirm')).toHaveLength(0);
  });

  it('accepts a password with upper+lower+digit even without a special character', async () => {
    mock.onPost('/auth/password-reset/confirm').reply(200, { message: 'Password has been reset successfully' });
    renderWithProviders(<PasswordResetConfirmForm token="reset-token-abc" />);

    await userEvent.type(screen.getByPlaceholderText('New Password'), 'Password1');
    await userEvent.type(screen.getByPlaceholderText('Confirm New Password'), 'Password1');
    await userEvent.click(screen.getByRole('button', { name: 'Reset Password' }));

    await screen.findByText('Password has been reset successfully');
    expect(mock.history.post.filter((r) => r.url === '/auth/password-reset/confirm')).toHaveLength(1);
  });
});
