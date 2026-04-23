import { useState, useMemo } from 'react';
import type { DisclosureCard } from '../types';
import { useStockPrice } from '../hooks/useStockPrice';
import { useAiOutlook } from '../hooks/useAiOutlook';
import { useDisclosureInsights } from '../hooks/useDisclosureInsights';
import { ToolTraceStrip } from '../components/ToolTraceStrip';
import type { StockQuote } from '../hooks/useStockPrice';
import { TrendingUp, TrendingDown, Sparkles } from 'lucide-react';

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
function AiOutlookCard({ ticker }: { ticker: string }) {
  const { title, data, loading, error } = useAiOutlook(ticker);

  return (
    <div className="rounded-xl border border-blue-100 bg-blue-50/60 p-3.5">
      <div className="flex items-start gap-2.5">
        <div className="shrink-0 w-7 h-7 rounded-lg bg-blue-600 flex items-center justify-center">
          <Sparkles size={13} color="#fff" strokeWidth={2} />
        </div>
        <div className="min-w-0">
          <p className="text-xs font-bold text-blue-900 mb-1">{title}</p>
          {loading && !data && (
            <div className="space-y-2 animate-pulse">
              <div className="h-3 w-full bg-blue-100/80 rounded" />
              <div className="h-3 w-4/5 bg-blue-100/80 rounded" />
            </div>
          )}
          {error && (
            <p className="text-[11px] text-red-700/90 leading-relaxed">
              Could not load outlook ({error}). Check that the backend and MCP are running.
            </p>
          )}
          {!loading && !error && data?.outlook && (
            <>
              <ToolTraceStrip traces={data.toolCalls} className="mb-2 justify-start" />
              <p className="text-[11px] text-blue-800/80 italic leading-relaxed">
                &ldquo;{data.outlook}&rdquo;
              </p>
              {data.tags.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {data.tags.map(t => (
                    <span key={t} className="text-[9px] font-bold bg-white/90 text-blue-700 px-1.5 py-0.5 rounded border border-blue-100 uppercase">
                      {t}
                    </span>
                  ))}
                </div>
              )}
            </>
          )}
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
    positive_medium: 'bg-cyan-50 text-cyan-800 border-cyan-100',
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
    { id: 'capex',     label: 'Capex'    },
  ], []);

  const { cards, toolCalls: insightToolCalls, loading: insightsLoading, error: insightsError } =
    useDisclosureInsights(currentAsset, activeTab);

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
            <AiOutlookCard ticker={currentAsset} />
          </div>
        )}

        {/* Other tabs: disclosure cards from /api/v1/analysis */}
        {activeTab !== 'overview' && (
          <div className="space-y-3">
            {insightsError && (
              <p className="text-[11px] text-red-700/90">
                Could not load insights ({insightsError}).
              </p>
            )}
            {!insightsLoading && !insightsError && insightToolCalls.length > 0 && (
              <ToolTraceStrip traces={insightToolCalls} className="justify-start mb-1" />
            )}
            {insightsLoading && cards.length === 0 && !insightsError && (
              <div className="space-y-3">
                {[1, 2, 3].map(i => (
                  <div key={i} className="rounded-xl border border-slate-100 bg-slate-50 p-3.5 animate-pulse space-y-2">
                    <div className="h-3 w-[75%] bg-slate-200 rounded" />
                    <div className="h-3 w-full bg-slate-200 rounded" />
                  </div>
                ))}
              </div>
            )}
            {!insightsLoading && !insightsError && cards.length === 0 && (
              <p className="text-[11px] text-slate-500">No insight cards returned for this ticker yet.</p>
            )}
            {cards.map((card: DisclosureCard, idx: number) => (
              <div
                key={`${card.title}-${idx}`}
                className="rounded-xl border border-slate-200 bg-white hover:border-indigo-200 transition-all duration-300 group overflow-hidden cursor-default"
                style={{ boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}
                onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.boxShadow = '0 4px 12px rgba(99,102,241,0.10)'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.boxShadow = '0 1px 2px rgba(0,0,0,0.04)'; }}
              >
                <div className="p-3.5">
                  <div className="flex items-start gap-2.5 mb-1.5">
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
                      <div className="mt-1">
                        <Badge level={card.impactLevel} label={card.impact} />
                      </div>
                    </div>
                  </div>

                  <div className="overflow-hidden transition-all duration-300 ease-in-out max-h-[2.4rem] group-hover:max-h-40">
                    <p className="text-[11px] text-slate-500 group-hover:text-slate-700 leading-relaxed transition-colors duration-200 pt-0.5">
                      {card.description}
                    </p>
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
