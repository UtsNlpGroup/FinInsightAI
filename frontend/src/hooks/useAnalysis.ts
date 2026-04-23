import { useState, useEffect } from 'react';
import {
  fetchAIThemes,
  fetchSentimentDivergence,
  fetchMarketNews,
  type SentimentBreakdown,
  type MarketNewsItem,
} from '../services/analysisApi';

// ── useAIThemes ───────────────────────────────────────────────────────────────

export function useAIThemes(ticker: string) {
  const [themes,  setThemes]  = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);

  useEffect(() => {
    if (!ticker) return;
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchAIThemes(ticker)
      .then(data  => { if (!cancelled) { setThemes(data);  setLoading(false); } })
      .catch(err  => { if (!cancelled) { setError((err as Error).message); setLoading(false); } });

    return () => { cancelled = true; };
  }, [ticker]);

  return { themes, loading, error };
}

// ── useSentimentDivergence ────────────────────────────────────────────────────

export function useSentimentDivergence(ticker: string) {
  const [breakdown, setBreakdown] = useState<SentimentBreakdown[]>([]);
  const [loading,   setLoading]   = useState(true);
  const [error,     setError]     = useState<string | null>(null);

  useEffect(() => {
    if (!ticker) return;
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchSentimentDivergence(ticker)
      .then(data  => { if (!cancelled) { setBreakdown(data); setLoading(false); } })
      .catch(err  => { if (!cancelled) { setError((err as Error).message); setLoading(false); } });

    return () => { cancelled = true; };
  }, [ticker]);

  return { breakdown, loading, error };
}

// ── useMarketNews ─────────────────────────────────────────────────────────────

export function useMarketNews(ticker: string) {
  const [items,   setItems]   = useState<MarketNewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);

  useEffect(() => {
    if (!ticker) return;
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchMarketNews(ticker)
      .then(data  => { if (!cancelled) { setItems(data);  setLoading(false); } })
      .catch(err  => { if (!cancelled) { setError((err as Error).message); setLoading(false); } });

    return () => { cancelled = true; };
  }, [ticker]);

  return { items, loading, error };
}
