/**
 * useStockPrice – fetches a real-time stock quote from the backend.
 *
 * Re-fetches automatically whenever `ticker` changes.
 * Polls every 60 s so the price stays reasonably fresh while the
 * sidebar is visible.
 */

import { useState, useEffect, useRef } from 'react';

export interface StockQuote {
  ticker: string;
  company_name: string;
  price: number | null;
  previous_close: number | null;
  change: number | null;
  change_pct: number | null;
  currency: string | null;
  market_state: string | null;
  fifty_two_week_high: number | null;
  fifty_two_week_low: number | null;
}

const POLL_INTERVAL_MS = 60_000;

export function useStockPrice(ticker: string) {
  const [quote,   setQuote]   = useState<StockQuote | null>(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!ticker) return;

    let cancelled = false;

    const fetch_ = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`/api/v1/market/price/${encodeURIComponent(ticker)}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: StockQuote = await res.json();
        if (!cancelled) setQuote(data);
      } catch (err) {
        if (!cancelled) setError((err as Error).message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetch_();
    timerRef.current = setInterval(fetch_, POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [ticker]);

  return { quote, loading, error };
}
