/**
 * useAiOutlook – loads the AI Overall Outlook (10-K + market synthesis) for a ticker.
 *
 * Results are cached in sessionStorage keyed by ticker so the expensive
 * backend/agent call is only made once per company per browser session.
 */

import { useState, useEffect } from 'react';
import { fetchOverallOutlook, type OverallOutlookPayload } from '../services/analysisApi';

const TITLE = 'AI Overall Outlook';
const CACHE_PREFIX = 'ai_outlook_';

function readCache(ticker: string): OverallOutlookPayload | null {
  try {
    const raw = sessionStorage.getItem(CACHE_PREFIX + ticker);
    return raw ? (JSON.parse(raw) as OverallOutlookPayload) : null;
  } catch {
    return null;
  }
}

function writeCache(ticker: string, payload: OverallOutlookPayload): void {
  try {
    sessionStorage.setItem(CACHE_PREFIX + ticker, JSON.stringify(payload));
  } catch {
    // sessionStorage full or unavailable — silently skip caching
  }
}

export function useAiOutlook(ticker: string) {
  const [data, setData] = useState<OverallOutlookPayload | null>(() => readCache(ticker));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ticker) return;

    // Serve from cache if available — no fetch needed
    const cached = readCache(ticker);
    if (cached) {
      setData(cached);
      setLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;

    const run = async () => {
      setLoading(true);
      setError(null);
      setData(null);
      try {
        const payload = await fetchOverallOutlook(ticker);
        if (!cancelled) {
          writeCache(ticker, payload);
          setData(payload);
        }
      } catch (err) {
        if (!cancelled) {
          setData(null);
          setError((err as Error).message);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    run();
    return () => {
      cancelled = true;
    };
  }, [ticker]);

  return { title: TITLE, data, loading, error };
}
