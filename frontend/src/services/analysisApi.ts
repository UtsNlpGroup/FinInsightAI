/**
 * analysisApi – thin HTTP layer for NLP analysis endpoints.
 *
 * Endpoints (all GET, prefix /api/v1/analysis):
 *   /outlook/{ticker}              → 10-K + market synthesis (AI Overall Outlook card)
 *   /risks/{ticker}                → risk insight cards (10-K)
 *   /growth-strategies/{ticker}    → growth & strategy cards
 *   /ai-themes/{ticker}           → string[] of recurring themes
 *   /sentiment-divergence/{ticker} → institutional vs social breakdown
 *   /market-news/{ticker}          → recent news items for the sentiment feed
 */

import type { DisclosureCard } from '../types';

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

export interface OverallOutlookPayload {
  ticker: string;
  outlook: string;
  tags: string[];
}

export type DisclosureInsightSegment = 'risks' | 'growth-strategies';

const IMPACT_LEVELS = new Set<DisclosureCard['impactLevel']>([
  'high', 'medium', 'low', 'positive_high', 'positive_medium',
]);

function normalizeImpactLevel(raw: string): DisclosureCard['impactLevel'] {
  const s = raw.toLowerCase().replace(/-/g, '_') as DisclosureCard['impactLevel'];
  return IMPACT_LEVELS.has(s) ? s : 'medium';
}

function apiCardToDisclosureCard(raw: Record<string, unknown>, index: number): DisclosureCard {
  const title = String(raw.title ?? `Insight ${index + 1}`);
  return {
    title,
    pageRef: String(raw.page_ref ?? raw.pageRef ?? '10-K'),
    description: String(raw.description ?? ''),
    impact: String(raw.impact ?? '—'),
    impactLevel: normalizeImpactLevel(String(raw.impact_level ?? raw.impactLevel ?? 'medium')),
    icon: String(raw.icon ?? '📄'),
  };
}

// ── Fetch helpers ─────────────────────────────────────────────────────────────

export async function fetchDisclosureInsights(
  ticker: string,
  segment: DisclosureInsightSegment,
): Promise<DisclosureCard[]> {
  const path =
    segment === 'growth-strategies' ? 'growth-strategies' : segment;
  const res = await fetch(`${BASE}/${path}/${encodeURIComponent(ticker)}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  const cards = Array.isArray(data.cards) ? data.cards : [];
  return cards.map((c: unknown, i: number) =>
    apiCardToDisclosureCard(c as Record<string, unknown>, i),
  );
}

export async function fetchOverallOutlook(ticker: string): Promise<OverallOutlookPayload> {
  const res = await fetch(`${BASE}/outlook/${encodeURIComponent(ticker)}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return {
    ticker: String(data.ticker ?? ticker).toUpperCase(),
    outlook: String(data.outlook ?? ''),
    tags: Array.isArray(data.tags) ? data.tags.map((t: unknown) => String(t)) : [],
  };
}

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
