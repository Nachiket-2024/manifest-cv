import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClientProvider } from '@tanstack/react-query';
import { ChakraProvider, defaultSystem } from '@chakra-ui/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import MockAdapter from 'axios-mock-adapter';

import api from '@/mystic_auth/api/axiosInstance';
import { queryClient } from '@/mystic_auth/core/queryClient';
import ResumeEditorPage from '@/resumes/ResumeEditorPage';

const mock = new MockAdapter(api);

const DRAFT: import('@/api/resume_api').ResumeDraftRead = {
  id: 1,
  job_description: 'Backend engineer at Example Corp',
  resume_content: 'Original resume content',
  status: 'draft',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

function renderEditor() {
  // Uses the app's own singleton queryClient (not a fresh per-test
  // instance) — resumeMutations.ts imports its `queryClient` from
  // core/queryClient.ts directly (see that module's own docstring on why:
  // code outside the React tree needs to reach it too), so a mutation's
  // onSuccess writes into that singleton specifically. A fresh
  // `new QueryClient()` here would leave this page's own useQuery hooks
  // (reading from this Provider's context) never seeing those writes.
  return render(
    <QueryClientProvider client={queryClient}>
      <ChakraProvider value={defaultSystem}>
        <MemoryRouter initialEntries={['/resumes/1']}>
          <Routes>
            <Route path="/resumes/:draftId" element={<ResumeEditorPage />} />
          </Routes>
        </MemoryRouter>
      </ChakraProvider>
    </QueryClientProvider>
  );
}

describe('ResumeEditorPage', () => {
  beforeEach(() => {
    mock.reset();
    queryClient.clear();
    mock.onGet('/resumes/1').reply(200, DRAFT);
  });

  it('renders the loaded draft content', async () => {
    renderEditor();

    expect(await screen.findByDisplayValue('Original resume content')).toBeInTheDocument();
  });

  it('shows an error state when the draft fails to load', async () => {
    mock.reset();
    mock.onGet('/resumes/1').reply(500);
    renderEditor();

    expect(await screen.findByText(/failed to load this resume/i)).toBeInTheDocument();
  });

  // Regression test for a data-loss bug: refining via AI (a real Gemini
  // call, several seconds of latency) used to leave the content textarea
  // editable while the mutation was in flight. Its onSuccess handler
  // (useUpdateResumeDraftMutation) calls setQueryData with the server's
  // new content, which the page's own draft->content sync effect then
  // force-writes into the textarea — silently overwriting anything the
  // user typed in the meantime. Disabling the textarea while the mutation
  // is pending closes that race entirely; this test locks that in.
  it('disables the content textarea while a refine/save mutation is in flight, preventing edits from being silently clobbered', async () => {
    let resolveUpdate: (() => void) | undefined;
    mock.onPut('/resumes/1').reply(() => {
      return new Promise((resolve) => {
        resolveUpdate = () => resolve([200, { ...DRAFT, resume_content: 'AI-refined content' }]);
      });
    });

    renderEditor();
    const user = userEvent.setup();

    const textarea = await screen.findByDisplayValue('Original resume content');
    const refinementInput = screen.getByPlaceholderText(/describe the change you want/i);
    await user.type(refinementInput, 'emphasize backend experience');
    await user.click(screen.getByRole('button', { name: /refine with ai/i }));

    await waitFor(() => expect(textarea).toBeDisabled());

    // Simulates the user typing more while the AI call is still in
    // flight — this must not reach the DOM value while disabled.
    expect(textarea).toHaveValue('Original resume content');

    resolveUpdate?.();

    await waitFor(() => expect(textarea).toHaveValue('AI-refined content'));
    expect(textarea.hasAttribute('disabled')).toBe(false);
  });

  it('submits a direct content edit via PUT /resumes/:id', async () => {
    mock.onPut('/resumes/1').reply(200, { ...DRAFT, resume_content: 'Edited by hand' });

    renderEditor();
    const user = userEvent.setup();

    const textarea = await screen.findByDisplayValue('Original resume content');
    await user.clear(textarea);
    await user.type(textarea, 'Edited by hand');
    await user.click(screen.getByRole('button', { name: /save changes/i }));

    await waitFor(() => expect(mock.history.put.length).toBe(1));
    expect(JSON.parse(mock.history.put[0].data)).toEqual({ content: 'Edited by hand' });
  });

  it('shows an error state when the templates fetch fails after approval', async () => {
    mock.onGet('/resumes/1').reply(200, { ...DRAFT, status: 'approved' });
    mock.onGet('/resumes/1/templates').reply(500);
    mock.onGet('/resumes/1/finalize').reply(404);

    renderEditor();

    expect(await screen.findByText(/failed to load templates/i)).toBeInTheDocument();
  });

  it('shows an error state when checking for a finalized document fails after approval', async () => {
    mock.onGet('/resumes/1').reply(200, { ...DRAFT, status: 'approved' });
    mock.onGet('/resumes/1/templates').reply(200, [{ id: 'classic', label: 'Classic' }]);
    mock.onGet('/resumes/1/finalize').reply(500);

    renderEditor();

    expect(await screen.findByText(/failed to check for a finalized pdf/i)).toBeInTheDocument();
  });

  it('disables the content textarea once the draft is approved', async () => {
    mock.onGet('/resumes/1').reply(200, { ...DRAFT, status: 'approved' });
    mock.onGet('/resumes/1/templates').reply(200, [{ id: 'classic', label: 'Classic' }]);
    mock.onGet('/resumes/1/finalize').reply(404);

    renderEditor();

    const textarea = await screen.findByDisplayValue('Original resume content');
    expect(textarea).toBeDisabled();
  });

  it('approves the draft via POST /resumes/:id/approve', async () => {
    mock.onPost('/resumes/1/approve').reply(200, { ...DRAFT, status: 'approved' });

    renderEditor();
    const user = userEvent.setup();

    await screen.findByDisplayValue('Original resume content');
    await user.click(screen.getByRole('button', { name: /approve resume/i }));

    await waitFor(() => expect(mock.history.post.filter((r) => r.url === '/resumes/1/approve')).toHaveLength(1));
    expect(await screen.findByText('approved')).toBeInTheDocument();
  });

  it('finalizes the resume with the selected template via POST /resumes/:id/finalize', async () => {
    mock.onGet('/resumes/1').reply(200, { ...DRAFT, status: 'approved' });
    mock.onGet('/resumes/1/templates').reply(200, [{ id: 'classic', label: 'Classic' }]);
    mock.onGet('/resumes/1/finalize').reply(404);
    mock.onPost('/resumes/1/finalize').reply(200, {
      id: 1,
      resume_draft_id: 1,
      template_id: 'classic',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    });

    renderEditor();
    const user = userEvent.setup();

    await user.click(await screen.findByRole('button', { name: /use this template/i }));

    await waitFor(() => expect(mock.history.post.filter((r) => r.url === '/resumes/1/finalize')).toHaveLength(1));
    expect(JSON.parse(mock.history.post.find((r) => r.url === '/resumes/1/finalize')!.data)).toEqual({
      template_id: 'classic',
    });
    expect(await screen.findByText(/final resume ready/i)).toBeInTheDocument();
  });

  it('saves a tracked application via POST /applications/ once a finalized document exists', async () => {
    mock.onGet('/resumes/1').reply(200, { ...DRAFT, status: 'approved' });
    mock.onGet('/resumes/1/templates').reply(200, [{ id: 'classic', label: 'Classic' }]);
    mock.onGet('/resumes/1/finalize').reply(200, {
      id: 1,
      resume_draft_id: 1,
      template_id: 'classic',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    });
    mock.onPost('/applications/').reply(201, {
      id: 1,
      company_name: 'Example Corp',
      application_date: '2026-01-02',
      application_time: null,
      status: 'applied',
      template_id_snapshot: 'classic',
      resume_content_snapshot: 'Original resume content',
      created_at: '2026-01-02T00:00:00Z',
      updated_at: '2026-01-02T00:00:00Z',
    });

    renderEditor();
    const user = userEvent.setup();

    await screen.findByText(/final resume ready/i);
    await user.type(screen.getByPlaceholderText(/company name/i), 'Example Corp');
    await user.click(screen.getByRole('button', { name: /save application/i }));

    await waitFor(() => expect(mock.history.post.filter((r) => r.url === '/applications/')).toHaveLength(1));
    const body = JSON.parse(mock.history.post.find((r) => r.url === '/applications/')!.data);
    expect(body).toMatchObject({ resume_draft_id: 1, company_name: 'Example Corp', status: 'applied' });
  });

  it('shows an error toast-equivalent alert when saving an application fails', async () => {
    mock.onGet('/resumes/1').reply(200, { ...DRAFT, status: 'approved' });
    mock.onGet('/resumes/1/templates').reply(200, [{ id: 'classic', label: 'Classic' }]);
    mock.onGet('/resumes/1/finalize').reply(200, {
      id: 1,
      resume_draft_id: 1,
      template_id: 'classic',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    });
    mock.onPost('/applications/').reply(500);

    renderEditor();
    const user = userEvent.setup();

    await screen.findByText(/final resume ready/i);
    await user.type(screen.getByPlaceholderText(/company name/i), 'Example Corp');
    await user.click(screen.getByRole('button', { name: /save application/i }));

    expect(await screen.findByText(/failed to save application/i)).toBeInTheDocument();
  });
});
