/**
 * Component tests for TickerBand.tsx – the scrolling market ticker strip.
 */

import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import TickerBand from '../components/TickerBand';

// Mock the fetch call that TickerBand may use to get market data
beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      prices: [
        { ticker: 'AAPL', price: 185.50, change_pct: 1.25 },
        { ticker: 'MSFT', price: 415.20, change_pct: -0.34 },
        { ticker: 'NVDA', price: 875.00, change_pct: 2.18 },
      ],
    }),
  }));
});

describe('TickerBand', () => {
  it('renders without crashing', () => {
    const { container } = render(<TickerBand />);
    expect(container).toBeTruthy();
  });

  it('renders a container element', () => {
    const { container } = render(<TickerBand />);
    expect(container.firstChild).not.toBeNull();
  });
});
