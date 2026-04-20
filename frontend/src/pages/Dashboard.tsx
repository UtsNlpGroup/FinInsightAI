import { useState, useMemo } from 'react';
import type { DisclosureCard } from '../types';
import {
  AI_OUTLOOK,
  DISCLOSURE_META, DISCLOSURE_KEY_RISKS, DISCLOSURE_GROWTH_DRIVERS,
  DISCLOSURE_STRATEGIC_FOCUS, DISCLOSURE_FINANCIAL_TRENDS,
} from '../data/mockData';
import { useStockPrice } from '../hooks/useStockPrice';
import type { StockQuote } from '../hooks/useStockPrice';
import { TrendingUp, TrendingDown, Sparkles, ChevronRight } from 'lucide-react';

function fmt(n: number | null | undefined, decimals = 2): string {
  if (n == null) return '—';
  return n.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

// ── Compact price chip ────────────────────────────────────────────────────────
function PriceChip({ quote, loading }: { quote: StockQuote | null; loading: boolean }) {
  const up    = (quote?.change_pct ?? 0) >= 0;
  const color = up ? '#10B981' : '#EF4444';
  const bg    = up ? '#DCFCE7' : '#FEF2F2';
  const Icon  = up ? TrendingUp : TrendingDown;

  if (loading && !quote) {
    return <div className="h-5 w-24 bg-slate-200 rounded-full animate-pulse" />;
  }
  if (!quote) return null;

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <span className="text-2xl font-extrabold text-slate-900 tracking-tight">
        {quote.currency === 'USD' ? '$' : ''}{fmt(quote.price)}
      </span>
      <span
        className="flex items-center gap-0.5 text-xs font-bold px-2 py-0.5 rounded-full"
        style={{ background: bg, color }}
      >
        <Icon size={10} strokeWidth={2.5} />
        {up ? '+' : ''}{fmt(quote.change_pct, 2)}%
      </span>
      {quote.market_state && (
        <span
          className="text-[9px] font-bold px-1.5 py-0.5 rounded uppercase"
          style={{
            background: quote.market_state === 'REGULAR' ? '#DCFCE7' : '#F3F4F6',
            color:      quote.market_state === 'REGULAR' ? '#15803D' : '#6B7280',
          }}
        >
          {quote.market_state === 'REGULAR' ? 'Live' : quote.market_state}
        </span>
      )}
    </div>
  );
}

// ── Range bar ─────────────────────────────────────────────────────────────────
function RangeBar({ quote }: { quote: StockQuote | null }) {
  if (!quote || !quote.fifty_two_week_low || !quote.fifty_two_week_high) return null;

  const lo  = quote.fifty_two_week_low;
  const hi  = quote.fifty_two_week_high;
  const cur = quote.price ?? lo;
  const pct = Math.min(1, Math.max(0, (cur - lo) / (hi - lo))) * 100;

  return (
    <div className="mt-3 px-4 py-2.5 bg-slate-50 rounded-xl border border-slate-100">
      <div className="flex justify-between text-[10px] font-semibold text-slate-400 mb-1.5">
        <span>52W LOW</span>
        <span>52W HIGH</span>
      </div>
      <div className="relative h-1.5 bg-slate-200 rounded-full">
        <div
          className="absolute inset-y-0 left-0 rounded-full"
          style={{ width: `${pct}%`, background: 'linear-gradient(90deg, #6366F1, #8B5CF6)' }}
        />
        <div
          className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full border-2 border-white shadow"
          style={{ left: `calc(${pct}% - 6px)`, background: '#6366F1' }}
        />
      </div>
      <div className="flex justify-between text-[10px] font-bold text-slate-500 mt-1.5">
        <span>${fmt(lo)}</span>
        <span>${fmt(hi)}</span>
      </div>
    </div>
  );
}

// ── Disclosure card badge ─────────────────────────────────────────────────────
const Badge = ({ level, label }: { level: string; label: string }) => {
  const variants: Record<string, string> = {
    high:          'bg-red-50 text-red-700 border-red-100',
    medium:        'bg-amber-50 text-amber-700 border-amber-100',
    positive_high: 'bg-emerald-50 text-emerald-700 border-emerald-100',
    low:           'bg-slate-50 text-slate-600 border-slate-100',
  };
  return (
    <span className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${variants[level] || variants.low}`}>
      {label}
    </span>
  );
};

// ── Main ─────────────────────────────────────────────────────────────────────

export default function RefinedDashboard({ currentAsset = 'AAPL' }: { currentAsset?: string }) {
  const [activeTab, setActiveTab] = useState('risks');

  // Single fetch — shared across header, PriceChip and RangeBar
  const { quote, loading } = useStockPrice(currentAsset);

  const companyName = quote?.company_name || currentAsset;

  const TABS = useMemo(() => [
    { id: 'risks',     label: 'Risks',    data: DISCLOSURE_KEY_RISKS },
    { id: 'growth',    label: 'Growth',   data: DISCLOSURE_GROWTH_DRIVERS },
    { id: 'strategic', label: 'Strategy', data: DISCLOSURE_STRATEGIC_FOCUS },
    { id: 'trends',    label: 'Trends',   data: DISCLOSURE_FINANCIAL_TRENDS },
  ], []);

  const activeContent = useMemo(
    () => TABS.find(t => t.id === activeTab)?.data || [],
    [activeTab, TABS],
  );

  return (
    <div className="flex flex-col h-full antialiased text-slate-900">

      {/* ── Header block ──────────────────────────────────────────────────── */}
      <div className="shrink-0 px-4 pt-5 pb-4 border-b border-slate-100">
        {/* Ticker + exchange row */}
        <div className="flex items-center gap-2 mb-2">
          <span className="bg-slate-900 text-white px-2 py-0.5 rounded text-[9px] font-black uppercase tracking-tighter">
            {currentAsset}
          </span>
          <span className="text-[10px] font-medium text-slate-400">Annual Filing</span>
        </div>

        {/* Company name — updates with selected ticker */}
        <h1 className="text-lg font-extrabold tracking-tight text-slate-900 leading-tight mb-2">
          {loading && !quote ? (
            <span className="inline-block h-5 w-40 bg-slate-200 rounded animate-pulse" />
          ) : (
            companyName
          )}
        </h1>

        {/* Live price chips */}
        <PriceChip quote={quote} loading={loading} />

        {/* 52W range bar */}
        <RangeBar quote={quote} />
      </div>

      {/* ── AI Insight ────────────────────────────────────────────────────── */}
      <div className="shrink-0 mx-4 mt-4 px-3 py-3 rounded-xl border border-blue-100 bg-blue-50/60">
        <div className="flex items-start gap-2.5">
          <div className="shrink-0 w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center">
            <Sparkles size={13} color="#fff" strokeWidth={2} />
          </div>
          <div className="min-w-0">
            <p className="text-xs font-bold text-blue-900 mb-1">{AI_OUTLOOK.title}</p>
            <p className="text-[11px] text-blue-800/80 italic leading-relaxed line-clamp-3">
              "{AI_OUTLOOK.quote}"
            </p>
            <div className="flex flex-wrap gap-1.5 mt-2">
              {AI_OUTLOOK.tags.map(t => (
                <span key={t} className="text-[9px] font-bold bg-white/90 text-blue-700 px-1.5 py-0.5 rounded border border-blue-100 uppercase">
                  {t}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── 10-K Deep Dive ────────────────────────────────────────────────── */}
      <div className="shrink-0 px-4 mt-5 mb-3">
        <p className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-0.5">
          {DISCLOSURE_META.title}
        </p>
        <p className="text-[10px] text-slate-400">{DISCLOSURE_META.subtitle}</p>
      </div>

      {/* Tab bar — scrollable */}
      <div className="shrink-0 px-4 mb-3">
        <div className="flex gap-1 p-1 bg-slate-100 rounded-xl overflow-x-auto no-scrollbar">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 min-w-0 px-2 py-1.5 text-[11px] font-bold rounded-lg whitespace-nowrap transition-all ${
                activeTab === tab.id
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Card list — scrollable region */}
      <div className="flex-1 overflow-y-auto px-4 pb-6 space-y-3">
        {activeContent.map((card: DisclosureCard) => (
          <div
            key={card.title}
            className="rounded-xl border border-slate-200 bg-white hover:border-indigo-200 transition-colors group overflow-hidden"
          >
            <div className="p-3.5">
              <div className="flex items-start gap-2.5 mb-2">
                <div className="shrink-0 w-7 h-7 flex items-center justify-center bg-slate-50 group-hover:bg-indigo-50 rounded-lg transition-colors text-base leading-none">
                  {card.icon}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-1">
                    <h4 className="text-[12px] font-bold text-slate-900 leading-snug">{card.title}</h4>
                    <span className="shrink-0 text-[9px] font-mono text-slate-400 bg-slate-50 px-1.5 py-0.5 rounded">
                      {card.pageRef}
                    </span>
                  </div>
                </div>
              </div>

              <p className="text-[11px] text-slate-600 leading-relaxed line-clamp-2 mb-2.5">
                {card.description}
              </p>

              <div className="flex items-center justify-between">
                <Badge level={card.impactLevel} label={card.impact} />
                <button className="flex items-center gap-0.5 text-[10px] font-bold text-indigo-600 hover:text-indigo-800 transition-colors">
                  Details <ChevronRight size={10} strokeWidth={2.5} />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

    </div>
  );
}
