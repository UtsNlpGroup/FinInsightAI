/**
 * Unit tests for pure utility functions extracted from App.tsx.
 *
 * Tests the relativeTime helper and other pure logic.
 */

import { describe, expect, it, beforeEach, afterEach, vi } from 'vitest';

// ── relativeTime (extracted from App.tsx for testability) ─────────────────────

function relativeTime(ts: number): string {
  const diff = Date.now() - ts;
  const min = Math.floor(diff / 60_000);
  const hr = Math.floor(diff / 3_600_000);
  const day = Math.floor(diff / 86_400_000);
  if (min < 1) return 'Just now';
  if (min < 60) return `${min}m ago`;
  if (hr < 24) return `${hr}h ago`;
  return `${day}d ago`;
}

describe('relativeTime', () => {
  const NOW = 1_700_000_000_000; // fixed timestamp

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(NOW);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns "Just now" for timestamp less than 1 minute ago', () => {
    const ts = NOW - 30_000; // 30 seconds ago
    expect(relativeTime(ts)).toBe('Just now');
  });

  it('returns "1m ago" for exactly 1 minute ago', () => {
    const ts = NOW - 60_000;
    expect(relativeTime(ts)).toBe('1m ago');
  });

  it('returns "45m ago" for 45 minutes ago', () => {
    const ts = NOW - 45 * 60_000;
    expect(relativeTime(ts)).toBe('45m ago');
  });

  it('returns "59m ago" for 59 minutes ago (below 1 hour threshold)', () => {
    const ts = NOW - 59 * 60_000;
    expect(relativeTime(ts)).toBe('59m ago');
  });

  it('returns "1h ago" for exactly 1 hour ago', () => {
    const ts = NOW - 3_600_000;
    expect(relativeTime(ts)).toBe('1h ago');
  });

  it('returns "12h ago" for 12 hours ago', () => {
    const ts = NOW - 12 * 3_600_000;
    expect(relativeTime(ts)).toBe('12h ago');
  });

  it('returns "23h ago" for 23 hours ago (below 1 day threshold)', () => {
    const ts = NOW - 23 * 3_600_000;
    expect(relativeTime(ts)).toBe('23h ago');
  });

  it('returns "1d ago" for exactly 24 hours ago', () => {
    const ts = NOW - 86_400_000;
    expect(relativeTime(ts)).toBe('1d ago');
  });

  it('returns "7d ago" for 7 days ago', () => {
    const ts = NOW - 7 * 86_400_000;
    expect(relativeTime(ts)).toBe('7d ago');
  });

  it('returns "Just now" for ts equal to now', () => {
    expect(relativeTime(NOW)).toBe('Just now');
  });
});


// ── Ticker validation helpers ─────────────────────────────────────────────────

function isValidTicker(ticker: string): boolean {
  return /^[A-Z]{1,10}$/.test(ticker.toUpperCase());
}

describe('isValidTicker', () => {
  it('accepts single letter ticker', () => {
    expect(isValidTicker('A')).toBe(true);
  });

  it('accepts standard 4-letter ticker', () => {
    expect(isValidTicker('AAPL')).toBe(true);
  });

  it('accepts lowercase (normalised to uppercase)', () => {
    expect(isValidTicker('msft')).toBe(true);
  });

  it('rejects empty string', () => {
    expect(isValidTicker('')).toBe(false);
  });

  it('rejects ticker with numbers', () => {
    expect(isValidTicker('AAPL123')).toBe(false);
  });

  it('rejects ticker longer than 10 chars', () => {
    expect(isValidTicker('TOOLONGTICKER')).toBe(false);
  });
});


// ── Sentiment label helper ────────────────────────────────────────────────────

function sentimentToColor(sentiment: string): string {
  switch (sentiment) {
    case 'bullish': return '#10B981';
    case 'bearish': return '#EF4444';
    case 'neutral': return '#6B7280';
    default: return '#9CA3AF';
  }
}

describe('sentimentToColor', () => {
  it('returns green for bullish', () => {
    expect(sentimentToColor('bullish')).toBe('#10B981');
  });

  it('returns red for bearish', () => {
    expect(sentimentToColor('bearish')).toBe('#EF4444');
  });

  it('returns grey for neutral', () => {
    expect(sentimentToColor('neutral')).toBe('#6B7280');
  });

  it('returns fallback for unknown sentiment', () => {
    expect(sentimentToColor('unknown')).toBe('#9CA3AF');
  });
});
