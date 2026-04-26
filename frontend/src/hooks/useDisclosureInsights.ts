/**
 * Loads 10-K insight cards for the Executive Dashboard (risks, growth).
 *
 * Results are cached in sessionStorage keyed by ticker + segment so the
 * expensive backend/agent call is only made once per combination per
 * browser session.
 */

import { useState, useEffect, useMemo } from 'react';
import type { DisclosureCard } from '../types';
import {
  fetchDisclosureInsights,
  type DisclosureInsightSegment,
} from '../services/analysisApi';

export type DashboardInsightTab = 'risks' | 'growth';

const CACHE_PREFIX = 'disclosure_insights_';

function cacheKey(ticker: string, segment: DisclosureInsightSegment): string {
  return `${CACHE_PREFIX}${ticker}_${segment}`;
}

function readCache(ticker: string, segment: DisclosureInsightSegment): DisclosureCard[] | null {
  try {
    const raw = sessionStorage.getItem(cacheKey(ticker, segment));
    return raw ? (JSON.parse(raw) as DisclosureCard[]) : null;
  } catch {
    return null;
  }
}

function writeCache(ticker: string, segment: DisclosureInsightSegment, cards: DisclosureCard[]): void {
  try {
    sessionStorage.setItem(cacheKey(ticker, segment), JSON.stringify(cards));
  } catch {
    // sessionStorage full or unavailable — silently skip caching
  }
}

function segmentForTab(tab: DashboardInsightTab): DisclosureInsightSegment {
  switch (tab) {
    case 'risks':
      return 'risks';
    case 'growth':
      return 'growth-strategies';
    default:
      return 'risks';
  }
}

export function useDisclosureInsights(ticker: string, activeTab: string) {
  const segment = useMemo(() => {
    if (activeTab === 'risks' || activeTab === 'growth') {
      return segmentForTab(activeTab as DashboardInsightTab);
    }
    return null;
  }, [activeTab]);

  const [cards, setCards] = useState<DisclosureCard[]>(() => {
    if (!ticker || !segment) return [];
    return readCache(ticker, segment) ?? [];
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ticker || !segment) {
      setCards([]);
      setError(null);
      setLoading(false);
      return;
    }

    // Serve from cache if available — no fetch needed
    const cached = readCache(ticker, segment);
    if (cached) {
      setCards(cached);
      setLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;

    const run = async () => {
      setLoading(true);
      setError(null);
      setCards([]);
      try {
        const data = await fetchDisclosureInsights(ticker, segment);
        if (!cancelled) {
          writeCache(ticker, segment, data);
          setCards(data);
        }
      } catch (e) {
        if (!cancelled) {
          setCards([]);
          setError((e as Error).message);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    run();
    return () => {
      cancelled = true;
    };
  }, [ticker, segment]);

  return { cards, loading, error };
}
