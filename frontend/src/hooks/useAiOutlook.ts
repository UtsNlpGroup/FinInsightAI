/**
 * useAiOutlook – loads the AI Overall Outlook (10-K + market synthesis) for a ticker.
 *
 * One fetch per ticker change (no polling); the backend runs an agent call.
 */

import { useState, useEffect } from 'react';
import { fetchOverallOutlook, type OverallOutlookPayload } from '../services/analysisApi';

const TITLE = 'AI Overall Outlook';

export function useAiOutlook(ticker: string) {
  const [data, setData] = useState<OverallOutlookPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ticker) return;

    let cancelled = false;

    const run = async () => {
      setLoading(true);
      setError(null);
      setData(null);
      try {
        const payload = await fetchOverallOutlook(ticker);
        if (!cancelled) setData(payload);
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
