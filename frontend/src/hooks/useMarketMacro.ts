import { useState, useEffect } from 'react';

export interface MacroItem {
  key: string;
  label: string;
  ticker: string;
  price: number | null;
  change: number | null;
  change_pct: number | null;
  is_yield: boolean;
}

const POLL_MS = 60_000;

/**
 * Fetch live macro market indices from the backend.
 *
 * @param indices  Optional array of keys to fetch (e.g. ['SPX','NDX','TNX']).
 *                 Pass undefined / empty array to fetch all available indices.
 */
export function useMarketMacro(indices?: string[]) {
  const [items,   setItems]   = useState<MacroItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);

  const queryParam = indices && indices.length > 0
    ? `?indices=${indices.join(',')}`
    : '';

  useEffect(() => {
    let cancelled = false;

    const fetchMacro = async () => {
      try {
        const res = await fetch(`/api/v1/market/macro${queryParam}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: MacroItem[] = await res.json();
        if (!cancelled) { setItems(data); setError(null); }
      } catch (err) {
        if (!cancelled) setError((err as Error).message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchMacro();
    const timer = setInterval(fetchMacro, POLL_MS);
    return () => { cancelled = true; clearInterval(timer); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [queryParam]);

  return { items, loading, error };
}
