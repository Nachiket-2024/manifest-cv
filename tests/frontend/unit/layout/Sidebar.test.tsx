import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ChakraProvider, defaultSystem } from '@chakra-ui/react';
import { MemoryRouter } from 'react-router-dom';

import { useAuthStore } from '@/store/authStore';
import Sidebar from '@/layout/Sidebar';

const initialAuthState = useAuthStore.getState();

function seed(permissions: string[]) {
  useAuthStore.setState(initialAuthState, true);
  useAuthStore.getState().setAuthenticated(true);
  useAuthStore.getState().setProfile({
    name: 'Test User',
    email: 'user@example.com',
    role: 'user',
    permissions,
    has_password: true,
  });
}

function renderSidebar() {
  return render(
    <ChakraProvider value={defaultSystem}>
      <MemoryRouter>
        <Sidebar isOpen={false} onNavigate={() => {}} />
      </MemoryRouter>
    </ChakraProvider>
  );
}

describe('Sidebar', () => {
  beforeEach(() => {
    seed([]);
  });

  it('always shows links that require no permission', () => {
    renderSidebar();

    expect(screen.getByRole('link', { name: 'Dashboard' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Audit Log' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Profile' })).toBeInTheDocument();
  });

  it('hides Users and Policies links for a caller with no admin permissions', () => {
    renderSidebar();

    expect(screen.queryByRole('link', { name: 'Users' })).toBeNull();
    expect(screen.queryByRole('link', { name: 'Policies' })).toBeNull();
  });

  it('shows Users and Policies links once the caller holds the matching permissions', () => {
    seed(['users:list_all', 'policies:read']);
    renderSidebar();

    expect(screen.getByRole('link', { name: 'Users' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Policies' })).toBeInTheDocument();
  });
});
