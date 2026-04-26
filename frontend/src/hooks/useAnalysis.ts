import { useState, useEffect } from 'react';
import {
  fetchAIThemes,
  fetchSentimentDivergence,
  fetchMarketNews,
  type SentimentBreakdown,
  type MarketNewsItem,
} from '../services/analysisApi';

// ── sessionStorage cache helpers ─────────────────────────────────────────────

function readCache<T>(key: string): T | null {
  try {
    const raw = sessionStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

function writeCache<T>(key: string, value: T): void {
  try {
    sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    // sessionStorage full or unavailable — silently skip
  }
}

// ── useAIThemes ───────────────────────────────────────────────────────────────

export function useAIThemes(ticker: string) {
  const cacheKey = `ai_themes_${ticker}`;

  const [themes,  setThemes]  = useState<string[]>(() => readCache<string[]>(cacheKey) ?? []);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);

  useEffect(() => {
    if (!ticker) return;

    const cached = readCache<string[]>(cacheKey);
    if (cached) {
      setThemes(cached);
      setLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchAIThemes(ticker)
      .then(data => {
        if (!cancelled) {
          writeCache(cacheKey, data);
          setThemes(data);
          setLoading(false);
        }
      })
      .catch(err => {
        if (!cancelled) {
          setError((err as Error).message);
          setLoading(false);
        }
      });

    return () => { cancelled = true; };
  }, [ticker, cacheKey]);

  return { themes, loading, error };
}

// ── useSentimentDivergence ────────────────────────────────────────────────────

export function useSentimentDivergence(ticker: string) {
  const cacheKey = `sentiment_divergence_${ticker}`;

  const [breakdown, setBreakdown] = useState<SentimentBreakdown[]>(
    () => readCache<SentimentBreakdown[]>(cacheKey) ?? [],
  );
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);

  useEffect(() => {
    if (!ticker) return;

    const cached = readCache<SentimentBreakdown[]>(cacheKey);
    if (cached) {
      setBreakdown(cached);
      setLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchSentimentDivergence(ticker)
      .then(data => {
        if (!cancelled) {
          writeCache(cacheKey, data);
          setBreakdown(data);
          setLoading(false);
        }
      })
      .catch(err => {
        if (!cancelled) {
          setError((err as Error).message);
          setLoading(false);
        }
      });

    return () => { cancelled = true; };
  }, [ticker, cacheKey]);

  return { breakdown, loading, error };
}

// ── useMarketNews ─────────────────────────────────────────────────────────────

export function useMarketNews(ticker: string) {
  const cacheKey = `market_news_${ticker}`;

  const [items,   setItems]   = useState<MarketNewsItem[]>(
    () => readCache<MarketNewsItem[]>(cacheKey) ?? [],
  );
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);

  useEffect(() => {
    if (!ticker) return;

    const cached = readCache<MarketNewsItem[]>(cacheKey);
    if (cached) {
      setItems(cached);
      setLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchMarketNews(ticker)
      .then(data => {
        if (!cancelled) {
          writeCache(cacheKey, data);
          setItems(data);
          setLoading(false);
        }
      })
      .catch(err => {
        if (!cancelled) {
          setError((err as Error).message);
          setLoading(false);
        }
      });

    return () => { cancelled = true; };
  }, [ticker, cacheKey]);

  return { items, loading, error };
}
