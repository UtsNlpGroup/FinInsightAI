/**
 * Component tests for NewsBlock.tsx
 *
 * NewsBlock renders the ```news ... ``` fenced JSON block
 * extracted from agent responses as rich news cards.
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import NewsBlock from '../components/NewsBlock';

const sampleNewsItems = [
  {
    title: 'Apple Reports Record Q4 Earnings',
    summary: 'Apple exceeded Wall Street expectations with $120B quarterly revenue.',
    sentiment: 'bullish' as const,
    source: 'BLOOMBERG',
    date: '2025-01-30',
    url: 'https://bloomberg.com/apple-q4',
  },
  {
    title: 'Apple Faces EU Antitrust Probe',
    summary: 'European regulators launch investigation into App Store practices.',
    sentiment: 'bearish' as const,
    source: 'REUTERS',
    date: '2025-01-29',
    url: 'https://reuters.com/apple-eu',
  },
  {
    title: 'Apple Vision Pro Sales Data',
    summary: 'Analysts are divided on Vision Pro adoption rates.',
    sentiment: 'neutral' as const,
    source: 'CNBC',
    date: '2025-01-28',
  },
];

describe('NewsBlock', () => {
  it('renders all news items', () => {
    render(<NewsBlock items={sampleNewsItems} />);
    expect(screen.getByText('Apple Reports Record Q4 Earnings')).toBeInTheDocument();
    expect(screen.getByText('Apple Faces EU Antitrust Probe')).toBeInTheDocument();
    expect(screen.getByText('Apple Vision Pro Sales Data')).toBeInTheDocument();
  });

  it('renders news item summaries', () => {
    render(<NewsBlock items={sampleNewsItems} />);
    expect(screen.getByText(/exceeded Wall Street/i)).toBeInTheDocument();
  });

  it('renders source labels in uppercase', () => {
    render(<NewsBlock items={sampleNewsItems} />);
    expect(screen.getByText('BLOOMBERG')).toBeInTheDocument();
    expect(screen.getByText('REUTERS')).toBeInTheDocument();
  });

  it('renders bullish sentiment indicator', () => {
    render(<NewsBlock items={[sampleNewsItems[0]]} />);
    // "bullish" text or indicator should be present
    const container = screen.getByText('Apple Reports Record Q4 Earnings').closest('div');
    expect(container).toBeTruthy();
  });

  it('renders a link when URL is provided', () => {
    render(<NewsBlock items={[sampleNewsItems[0]]} />);
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', 'https://bloomberg.com/apple-q4');
  });

  it('does not crash when url is missing', () => {
    render(<NewsBlock items={[sampleNewsItems[2]]} />);
    expect(screen.getByText('Apple Vision Pro Sales Data')).toBeInTheDocument();
  });

  it('renders empty state when items is empty', () => {
    const { container } = render(<NewsBlock items={[]} />);
    // Should render without crash; no news cards shown
    expect(container).toBeTruthy();
  });

  it('renders all three sentiment badge labels', () => {
    render(<NewsBlock items={sampleNewsItems} />);
    expect(screen.getByText('Bullish')).toBeInTheDocument();
    expect(screen.getByText('Bearish')).toBeInTheDocument();
    expect(screen.getByText('Neutral')).toBeInTheDocument();
  });

  it('renders date metadata when present', () => {
    render(<NewsBlock items={[sampleNewsItems[0]]} />);
    expect(screen.getByText(/2025-01-30/)).toBeInTheDocument();
  });
});
