/**
 * analysisApi – thin HTTP layer for the three NLP analysis endpoints.
 *
 * Endpoints (all GET, prefix /api/v1/analysis):
 *   /ai-themes/{ticker}           → string[] of recurring themes
 *   /sentiment-divergence/{ticker} → institutional vs social breakdown
 *   /market-news/{ticker}          → recent news items for the sentiment feed
 */

const BASE = '/api/v1/analysis';

// ── Response types (mirror backend schemas/analysis.py) ──────────────────────

export interface SentimentBreakdown {
  label: string;       // e.g. "Institutional Focus"
  percentage: number;  // 0–100
  sentiment: string;   // "positive" | "negative" | "neutral"
}

export interface MarketNewsItem {
  title: string;
  summary: string;
  sentiment: string;   // "bullish" | "bearish" | "neutral"
  source?: string;
  time_ago?: string;
  url?: string;
}

// ── Fetch helpers ─────────────────────────────────────────────────────────────

export async function fetchAIThemes(ticker: string): Promise<string[]> {
  const res = await fetch(`${BASE}/ai-themes/${encodeURIComponent(ticker)}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return (data.themes as string[]) ?? [];
}

export async function fetchSentimentDivergence(ticker: string): Promise<SentimentBreakdown[]> {
  const res = await fetch(`${BASE}/sentiment-divergence/${encodeURIComponent(ticker)}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return (data.breakdown as SentimentBreakdown[]) ?? [];
}

export async function fetchMarketNews(ticker: string): Promise<MarketNewsItem[]> {
  const res = await fetch(`${BASE}/market-news/${encodeURIComponent(ticker)}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return (data.items as MarketNewsItem[]) ?? [];
}
