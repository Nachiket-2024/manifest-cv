import type { ComponentProps } from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChakraProvider, defaultSystem } from '@chakra-ui/react';

import Pager from '@/ui/Pager';

function renderPager(props: Partial<ComponentProps<typeof Pager>> = {}) {
  const onOffsetChange = vi.fn();
  const utils = render(
    <ChakraProvider value={defaultSystem}>
      <Pager offset={0} limit={20} rowCount={20} onOffsetChange={onOffsetChange} {...props} />
    </ChakraProvider>
  );
  return { onOffsetChange, ...utils };
}

describe('Pager', () => {
  it('renders nothing when there is only one page (first page, fewer rows than the limit)', () => {
    const { container } = renderPager({ offset: 0, limit: 20, rowCount: 5 });
    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing while the first page is still loading (rowCount undefined)', () => {
    const { container } = renderPager({ offset: 0, limit: 20, rowCount: undefined });
    expect(container).toBeEmptyDOMElement();
  });

  it('disables Previous on the first page and enables Next when a full page came back', () => {
    renderPager({ offset: 0, limit: 20, rowCount: 20 });

    expect(screen.getByRole('button', { name: 'Previous' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Next' })).toBeEnabled();
  });

  it('disables Next once a short page comes back (last page)', () => {
    renderPager({ offset: 20, limit: 20, rowCount: 5 });

    expect(screen.getByRole('button', { name: 'Previous' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled();
  });

  it('calls onOffsetChange with offset + limit when Next is clicked', async () => {
    const { onOffsetChange } = renderPager({ offset: 0, limit: 20, rowCount: 20 });
    const user = userEvent.setup();

    await user.click(screen.getByRole('button', { name: 'Next' }));

    expect(onOffsetChange).toHaveBeenCalledWith(20);
  });

  it('calls onOffsetChange with offset - limit when Previous is clicked', async () => {
    const { onOffsetChange } = renderPager({ offset: 40, limit: 20, rowCount: 20 });
    const user = userEvent.setup();

    await user.click(screen.getByRole('button', { name: 'Previous' }));

    expect(onOffsetChange).toHaveBeenCalledWith(20);
  });

  it('shows the current page number, 1-indexed', () => {
    renderPager({ offset: 40, limit: 20, rowCount: 20 });

    expect(screen.getByText('Page 3')).toBeInTheDocument();
  });
});
