/**
 * Loads 10-K insight cards for the Executive Dashboard (risks, growth, capex).
 */

import { useState, useEffect, useMemo } from 'react';
import type { DisclosureCard } from '../types';
import type { ToolCallTraceItem } from '../lib/toolCalls';
import {
  fetchDisclosureInsights,
  type DisclosureInsightSegment,
} from '../services/analysisApi';

export type DashboardInsightTab = 'risks' | 'growth' | 'capex';

function segmentForTab(tab: DashboardInsightTab): DisclosureInsightSegment {
  switch (tab) {
    case 'risks':
      return 'risks';
    case 'growth':
      return 'growth-strategies';
    case 'capex':
      return 'capex';
    default:
      return 'risks';
  }
}

export function useDisclosureInsights(ticker: string, activeTab: string) {
  const segment = useMemo(() => {
    if (activeTab === 'risks' || activeTab === 'growth' || activeTab === 'capex') {
      return segmentForTab(activeTab as DashboardInsightTab);
    }
    return null;
  }, [activeTab]);

  const [cards, setCards] = useState<DisclosureCard[]>([]);
  const [toolCalls, setToolCalls] = useState<ToolCallTraceItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ticker || !segment) {
      setCards([]);
      setToolCalls([]);
      setError(null);
      setLoading(false);
      return;
    }

    let cancelled = false;

    const run = async () => {
      setLoading(true);
      setError(null);
      setCards([]);
      setToolCalls([]);
      try {
        const data = await fetchDisclosureInsights(ticker, segment);
        if (!cancelled) {
          setCards(data.cards);
          setToolCalls(data.toolCalls);
        }
      } catch (e) {
        if (!cancelled) {
          setCards([]);
          setToolCalls([]);
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

  return { cards, toolCalls, loading, error };
}
