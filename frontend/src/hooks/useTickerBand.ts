import { useState, useEffect } from 'react';

export interface BandItem {
  ticker: string;
  company_name: string;
  price: number | null;
  change: number | null;
  change_pct: number | null;
  currency: string | null;
  sparkline: number[];
}

const POLL_MS = 60_000;

export function useTickerBand() {
  const [items,   setItems]   = useState<BandItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const fetchBand = async () => {
      try {
        const res = await fetch('/api/v1/market/prices/batch');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: BandItem[] = await res.json();
        if (!cancelled) {
          setItems(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) setError((err as Error).message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchBand();
    const timer = setInterval(fetchBand, POLL_MS);
    return () => { cancelled = true; clearInterval(timer); };
  }, []);

  return { items, loading, error };
}
