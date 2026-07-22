import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClientProvider } from '@tanstack/react-query';
import { ChakraProvider, defaultSystem } from '@chakra-ui/react';
import { MemoryRouter } from 'react-router-dom';
import MockAdapter from 'axios-mock-adapter';

import api from '@/api/axiosInstance';
import { queryClient } from '@/core/queryClient';
import ApplicationsPage from '@/applications/ApplicationsPage';
import type { ApplicationRead } from '@/api/application_api';

const mock = new MockAdapter(api);

function application(id: number, companyName: string): ApplicationRead {
  return {
    id,
    company_name: companyName,
    application_date: '2026-01-01',
    application_time: null,
    status: 'applied',
    template_id_snapshot: 'classic',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  };
}

function renderPage() {
  return render(
    <QueryClientProvider client={queryClient}>
      <ChakraProvider value={defaultSystem}>
        <MemoryRouter>
          <ApplicationsPage />
        </MemoryRouter>
      </ChakraProvider>
    </QueryClientProvider>
  );
}

describe('ApplicationsPage pagination', () => {
  beforeEach(() => {
    mock.reset();
    queryClient.clear();
  });

  it('requests the default page size and offset', async () => {
    mock.onGet('/applications/').reply((config) => {
      expect(config.params).toEqual({ limit: 20, offset: 0 });
      return [200, [application(1, 'Acme Corp')]];
    });

    renderPage();

    await screen.findByText('Acme Corp');
    expect(screen.queryByRole('button', { name: 'Next' })).toBeNull();
  });

  it('advances to the next page and back, requesting the right offset each time', async () => {
    const fullPage = Array.from({ length: 20 }, (_, i) => application(20 - i, `Company ${20 - i}`));
    mock.onGet('/applications/').reply((config) => {
      if (config.params.offset === 0) return [200, fullPage];
      if (config.params.offset === 20) return [200, [application(21, 'Company 21')]];
      return [200, []];
    });

    renderPage();
    const user = userEvent.setup();

    await screen.findByText('Company 20');
    expect(screen.getByText('Page 1')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Next' }));

    await screen.findByText('Company 21');
    expect(screen.getByText('Page 2')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled();

    await user.click(screen.getByRole('button', { name: 'Previous' }));

    await screen.findByText('Company 20');
    expect(screen.getByText('Page 1')).toBeInTheDocument();
  });

  it('steps back a page after deleting the only row on a non-first page', async () => {
    const fullPage = Array.from({ length: 20 }, (_, i) => application(20 - i, `Company ${20 - i}`));
    let secondPageDeleted = false;
    mock.onGet('/applications/').reply((config) => {
      if (config.params.offset === 0) return [200, fullPage];
      if (config.params.offset === 20) return [200, secondPageDeleted ? [] : [application(21, 'Company 21')]];
      return [200, []];
    });
    mock.onDelete('/applications/21').reply(() => {
      secondPageDeleted = true;
      return [200];
    });

    renderPage();
    const user = userEvent.setup();

    await screen.findByText('Company 20');
    await user.click(screen.getByRole('button', { name: 'Next' }));
    await screen.findByText('Company 21');

    const rows = screen.getAllByRole('row');
    const targetRow = rows.find((r) => r.textContent?.includes('Company 21'));
    await user.click(within(targetRow as HTMLElement).getByRole('button', { name: /delete/i }));

    await user.click(await screen.findByRole('button', { name: /^delete$/i }));

    await waitFor(() => expect(screen.getByText('Page 1')).toBeInTheDocument());
    await screen.findByText('Company 20');
  });
});
