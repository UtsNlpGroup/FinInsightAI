/**
 * useCompanies – fetches the list of tracked companies from the backend.
 *
 * The result is cached for the lifetime of the component that calls it.
 * A simple module-level cache prevents duplicate network requests when
 * multiple components mount at the same time.
 */

import { useState, useEffect } from 'react';

export interface Company {
  ticker: string;
  company_name: string;
  sector: string | null;
}

let _cache: Company[] | null = null;
let _promise: Promise<Company[]> | null = null;

async function fetchCompanies(): Promise<Company[]> {
  if (_cache) return _cache;
  if (!_promise) {
    _promise = fetch('/api/v1/market/companies')
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<Company[]>;
      })
      .then(data => {
        _cache = data;
        return data;
      })
      .catch(err => {
        _promise = null; // allow retry on next call
        throw err;
      });
  }
  return _promise;
}

export function useCompanies() {
  const [companies, setCompanies] = useState<Company[]>(_cache ?? []);
  const [loading,   setLoading]   = useState(!_cache);
  const [error,     setError]     = useState<string | null>(null);

  useEffect(() => {
    if (_cache) return; // already loaded
    fetchCompanies()
      .then(data => { setCompanies(data); setLoading(false); })
      .catch(err  => { setError((err as Error).message); setLoading(false); });
  }, []);

  return { companies, loading, error };
}
