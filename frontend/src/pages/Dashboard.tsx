import { useState, useMemo } from 'react';
import type { DisclosureCard } from '../types';
import {
  AI_OUTLOOK,
  DISCLOSURE_KEY_RISKS, DISCLOSURE_GROWTH_DRIVERS,
  DISCLOSURE_STRATEGIC_FOCUS, DISCLOSURE_FINANCIAL_TRENDS,
} from '../data/mockData';
import { useStockPrice } from '../hooks/useStockPrice';
import type { StockQuote } from '../hooks/useStockPrice';
import { TrendingUp, TrendingDown, Sparkles, ChevronRight } from 'lucide-react';

function fmt(n: number | null | undefined, decimals = 2): string {
  if (n == null) return '—';
  return n.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

// ── Price + range (used only inside Overview tab) ─────────────────────────────
function PriceBlock({ quote, loading }: { quote: StockQuote | null; loading: boolean }) {
  const up    = (quote?.change_pct ?? 0) >= 0;
  const color = up ? '#10B981' : '#EF4444';
  const bg    = up ? '#DCFCE7' : '#FEF2F2';
  const Icon  = up ? TrendingUp : TrendingDown;

  if (loading && !quote) {
    return (
      <div className="rounded-xl border border-slate-100 bg-slate-50 p-4 space-y-3 animate-pulse">
        <div className="h-8 w-32 bg-slate-200 rounded" />
        <div className="h-4 w-full bg-slate-200 rounded" />
      </div>
    );
  }
  if (!quote) return null;

  // 52W range
  const lo  = quote.fifty_two_week_low;
  const hi  = quote.fifty_two_week_high;
  const pct = lo && hi
    ? Math.min(1, Math.max(0, ((quote.price ?? lo) - lo) / (hi - lo))) * 100
    : null;

  return (
    <div className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3.5">
      {/* Price row */}
      <div className="flex items-center gap-2 flex-wrap mb-1">
        <span className="text-3xl font-extrabold text-slate-900 tracking-tight">
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

      {/* 52W range bar */}
      {pct !== null && lo && hi && (
        <div className="mt-3">
          <div className="flex justify-between text-[10px] font-semibold text-slate-400 mb-1.5">
            <span>52W LOW</span>
            <span>52W HIGH</span>
          </div>
          <div className="relative h-1.5 bg-slate-200 rounded-full">
            <div
              className="absolute inset-y-0 left-0 rounded-full"
              style={{ width: `${pct}%`, background: 'linear-gradient(90deg,#6366F1,#8B5CF6)' }}
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
      )}
    </div>
  );
}

// ── AI Outlook card (used only inside Overview tab) ───────────────────────────
function AiOutlookCard() {
  return (
    <div className="rounded-xl border border-blue-100 bg-blue-50/60 p-3.5">
      <div className="flex items-start gap-2.5">
        <div className="shrink-0 w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center">
          <Sparkles size={13} color="#fff" strokeWidth={2} />
        </div>
        <div className="min-w-0">
          <p className="text-xs font-bold text-blue-900 mb-1">{AI_OUTLOOK.title}</p>
          <p className="text-[11px] text-blue-800/80 italic leading-relaxed">
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
  );
}

// ── Disclosure card badge ─────────────────────────────────────────────────────
const Badge = ({ level, label }: { level: string; label: string }) => {
  const v: Record<string, string> = {
    high:          'bg-red-50 text-red-700 border-red-100',
    medium:        'bg-amber-50 text-amber-700 border-amber-100',
    positive_high: 'bg-emerald-50 text-emerald-700 border-emerald-100',
    low:           'bg-slate-50 text-slate-600 border-slate-100',
  };
  return (
    <span className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${v[level] || v.low}`}>
      {label}
    </span>
  );
};

// ── Main ─────────────────────────────────────────────────────────────────────

export default function RefinedDashboard({ currentAsset = 'AAPL' }: { currentAsset?: string }) {
  const [activeTab, setActiveTab] = useState('overview');

  const { quote, loading } = useStockPrice(currentAsset);
  const companyName = quote?.company_name || currentAsset;

  const TABS = useMemo(() => [
    { id: 'overview',  label: 'Overview' },
    { id: 'risks',     label: 'Risks'    },
    { id: 'growth',    label: 'Growth'   },
    { id: 'strategic', label: 'Strategy' },
    { id: 'trends',    label: 'Trends'   },
  ], []);

  const tabData: Record<string, DisclosureCard[]> = useMemo(() => ({
    risks:     DISCLOSURE_KEY_RISKS,
    growth:    DISCLOSURE_GROWTH_DRIVERS,
    strategic: DISCLOSURE_STRATEGIC_FOCUS,
    trends:    DISCLOSURE_FINANCIAL_TRENDS,
  }), []);

  return (
    <div className="flex flex-col h-full antialiased text-slate-900">

      {/* ── Header: ticker + company name only ────────────────────────────── */}
      <div className="shrink-0 px-4 pt-5 pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2 mb-1.5">
          <span className="bg-slate-900 text-white px-2 py-0.5 rounded text-[9px] font-black uppercase tracking-tighter">
            {currentAsset}
          </span>
          <span className="text-[10px] font-medium text-slate-400">Annual Filing</span>
        </div>
        <h1 className="text-base font-extrabold tracking-tight text-slate-900 leading-tight">
          {loading && !quote
            ? <span className="inline-block h-4 w-36 bg-slate-200 rounded animate-pulse" />
            : companyName}
        </h1>
      </div>

      {/* ── Tab bar ───────────────────────────────────────────────────────── */}
      <div className="shrink-0 px-3 pt-3 pb-2">
        <div className="flex gap-0.5 p-1 bg-slate-100 rounded-xl overflow-x-auto no-scrollbar">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 min-w-0 px-2 py-1.5 text-[10px] font-bold rounded-lg whitespace-nowrap transition-all ${
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

      {/* ── Scrollable content ────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-4 pb-6 pt-1">

        {/* Overview: price block + AI outlook only */}
        {activeTab === 'overview' && (
          <div className="space-y-3">
            <PriceBlock quote={quote} loading={loading} />
            <AiOutlookCard />
          </div>
        )}

        {/* Other tabs: disclosure cards */}
        {activeTab !== 'overview' && (
          <div className="space-y-3">
            {(tabData[activeTab] ?? []).map((card: DisclosureCard) => (
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
        )}

      </div>
    </div>
  );
}
