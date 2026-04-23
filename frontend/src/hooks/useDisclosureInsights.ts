/**
 * Loads 10-K insight cards for the Executive Dashboard (risks, growth).
 */

import { useState, useEffect, useMemo } from 'react';
import type { DisclosureCard } from '../types';
import {
  fetchDisclosureInsights,
  type DisclosureInsightSegment,
} from '../services/analysisApi';

export type DashboardInsightTab = 'risks' | 'growth';

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

  const [cards, setCards] = useState<DisclosureCard[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ticker || !segment) {
      setCards([]);
      setError(null);
      setLoading(false);
      return;
    }

    let cancelled = false;

    const run = async () => {
      setLoading(true);
      setError(null);
      setCards([]);
      try {
        const data = await fetchDisclosureInsights(ticker, segment);
        if (!cancelled) setCards(data);
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
