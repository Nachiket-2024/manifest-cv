import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClientProvider } from '@tanstack/react-query';
import { ChakraProvider, defaultSystem } from '@chakra-ui/react';
import { MemoryRouter } from 'react-router-dom';
import MockAdapter from 'axios-mock-adapter';

import api from '@/mystic_auth/api/axiosInstance';
import { queryClient } from '@/mystic_auth/core/queryClient';
import CareerKnowledgePage from '@/career_knowledge/CareerKnowledgePage';
import type { CareerKnowledgeBaseRead } from '@/api/career_knowledge_api';

const mock = new MockAdapter(api);

function knowledgeBase(overrides: Partial<CareerKnowledgeBaseRead> = {}): CareerKnowledgeBaseRead {
  return {
    id: 1,
    raw_input: 'Original pasted resume text',
    content: '## Experience\n\nSoftware Engineer at Acme',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

function renderPage() {
  // Same reasoning as resume_drafts_page.test.tsx: mutations write into the
  // app's own singleton queryClient, so the Provider here must use that same
  // instance, not a fresh one, for cache invalidation to be visible.
  return render(
    <QueryClientProvider client={queryClient}>
      <ChakraProvider value={defaultSystem}>
        <MemoryRouter>
          <CareerKnowledgePage />
        </MemoryRouter>
      </ChakraProvider>
    </QueryClientProvider>
  );
}

describe('CareerKnowledgePage', () => {
  beforeEach(() => {
    mock.reset();
    queryClient.clear();
  });

  it('shows the "get started" form when no knowledge base exists yet', async () => {
    mock.onGet('/career-knowledge/').reply(404);

    renderPage();

    await screen.findByText('Get started');
    expect(screen.getByRole('button', { name: 'Create knowledge base' })).toBeDisabled();
  });

  it('creates a knowledge base from pasted raw input', async () => {
    mock.onGet('/career-knowledge/').replyOnce(404);
    mock.onPost('/career-knowledge/').reply((config) => {
      expect(JSON.parse(config.data)).toEqual({ raw_input: 'My whole career, pasted in' });
      return [201, knowledgeBase()];
    });
    mock.onGet('/career-knowledge/').reply(200, knowledgeBase());

    renderPage();
    const user = userEvent.setup();

    await screen.findByText('Get started');
    await user.type(
      screen.getByPlaceholderText(/Paste your resume/i),
      'My whole career, pasted in'
    );
    await user.click(screen.getByRole('button', { name: 'Create knowledge base' }));

    await screen.findByText('Your knowledge base');
    expect(screen.getByText(/Software Engineer at Acme/)).toBeInTheDocument();
  });

  it('edits and saves the structured content, disabling save until dirty', async () => {
    mock.onGet('/career-knowledge/').reply(200, knowledgeBase());
    mock.onPut('/career-knowledge/').reply((config) => {
      expect(JSON.parse(config.data)).toEqual({ content: '## Experience\n\nSoftware Engineer at Acme, promoted' });
      return [200, knowledgeBase({ content: '## Experience\n\nSoftware Engineer at Acme, promoted' })];
    });

    renderPage();
    const user = userEvent.setup();

    await screen.findByText('Your knowledge base');
    const saveButton = screen.getByRole('button', { name: 'Save changes' });
    expect(saveButton).toBeDisabled();

    const textarea = screen.getByDisplayValue(/Software Engineer at Acme/);
    await user.type(textarea, ', promoted');
    expect(saveButton).toBeEnabled();

    await user.click(saveButton);

    // Once the mutation's response lands, local content is re-synced from
    // the server and the button goes back to disabled (no longer dirty).
    await waitFor(() => expect(saveButton).toBeDisabled());
  });

  it('toggles visibility of the original pasted text', async () => {
    mock.onGet('/career-knowledge/').reply(200, knowledgeBase());

    renderPage();
    const user = userEvent.setup();

    await screen.findByText('Your knowledge base');
    expect(screen.queryByText('Original pasted resume text')).toBeNull();

    await user.click(screen.getByRole('button', { name: /show original text/i }));
    expect(screen.getByText('Original pasted resume text')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /hide original text/i }));
    expect(screen.queryByText('Original pasted resume text')).toBeNull();
  });

  it('deletes the knowledge base after confirming, falling back to the "get started" form', async () => {
    let deleted = false;
    mock.onGet('/career-knowledge/').reply(() => (deleted ? [404] : [200, knowledgeBase()]));
    mock.onDelete('/career-knowledge/').reply(() => {
      deleted = true;
      return [200];
    });

    renderPage();
    const user = userEvent.setup();

    await screen.findByText('Your knowledge base');
    await user.click(screen.getByRole('button', { name: 'Start over' }));

    // Confirm dialog
    await user.click(await screen.findByRole('button', { name: /^delete$/i }));

    await screen.findByText('Get started');
  });
});
