import { useState } from 'react';
import { useMarketMacro } from '../hooks/useMarketMacro';
import { useAIThemes, useMarketNews } from '../hooks/useAnalysis';
import type { MarketNewsItem } from '../services/analysisApi';

// ── Shared primitives ────────────────────────────────────────────────────────

const SENTIMENT_CFG = {
  bullish:  { label: 'Bullish', icon: '↗', color: '#15803D', bg: '#F0FDF4', border: '#D1FAE5' },
  bearish:  { label: 'Bearish', icon: '↘', color: '#DC2626', bg: '#FEF2F2', border: '#FEE2E2' },
  neutral:  { label: 'Neutral', icon: '—',  color: '#6B7280', bg: '#F9FAFB', border: '#E5E7EB' },
} as const;

type SentimentKey = keyof typeof SENTIMENT_CFG;

function SentimentBadge({ sentiment }: { sentiment: string }) {
  const key = sentiment.toLowerCase() as SentimentKey;
  const cfg = SENTIMENT_CFG[key] ?? SENTIMENT_CFG.neutral;
  return (
    <span
      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wide border shrink-0"
      style={{ background: cfg.bg, color: cfg.color, borderColor: cfg.border }}
    >
      {cfg.icon} {cfg.label}
    </span>
  );
}

// ── Skeleton helpers ──────────────────────────────────────────────────────────

function SkeletonLine({ w = 'w-full', h = 'h-3' }: { w?: string; h?: string }) {
  return <div className={`${w} ${h} rounded animate-pulse`} style={{ background: '#E5E7EB' }} />;
}

// ── Macro card ────────────────────────────────────────────────────────────────

function MacroCard() {
  const { items, loading } = useMarketMacro();

  const fmt = (n: number | null | undefined, d = 2) =>
    n == null ? '—' : n.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });

  return (
    <div className="rounded-xl border border-slate-100 bg-white px-4 py-3.5">
      <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-3">
        Macro Market Context
      </p>
      {loading && items.length === 0 ? (
        <div className="space-y-1.5">
          {[1, 2, 3].map(i => (
            <div key={i} className="flex justify-between items-center px-3 py-2 rounded-lg animate-pulse" style={{ background: '#F9FAFB' }}>
              <div className="h-3 w-20 bg-slate-200 rounded" />
              <div className="h-3 w-12 bg-slate-200 rounded" />
            </div>
          ))}
        </div>
      ) : (
        <div className="space-y-1.5">
          {items.map(item => {
            const displayValue = item.is_yield
              ? `${fmt(item.price, 2)}%`
              : item.change_pct != null
              ? `${item.change_pct >= 0 ? '+' : ''}${fmt(item.change_pct, 2)}%`
              : '—';
            const color = item.is_yield
              ? '#6B7280'
              : (item.change_pct ?? 0) >= 0 ? '#10B981' : '#EF4444';
            return (
              <div key={item.key} className="flex justify-between items-center px-3 py-2 rounded-lg"
                style={{ background: '#F9FAFB', border: '1px solid #F3F4F6' }}>
                <span className="text-[11px] font-medium text-slate-600">{item.label}</span>
                <span className="text-[12px] font-bold" style={{ color }}>{displayValue}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Sentiment Speedometer ─────────────────────────────────────────────────────

function SentimentOverall({ breakdown }: { breakdown: SentimentBreakdown[] }) {
  const bullishPct = breakdown.find(b => b.sentiment === 'bullish')?.percentage ?? 0;
  const bearishPct = breakdown.find(b => b.sentiment === 'bearish')?.percentage ?? 0;
  const neutralPct = breakdown.find(b => b.sentiment === 'neutral')?.percentage ?? 0;

  const rows = [
    { label: 'Bearish', pct: bearishPct, color: '#EF4444', track: '#FEE2E2', dot: '#FCA5A5' },
    { label: 'Neutral', pct: neutralPct, color: '#D97706', track: '#FEF3C7', dot: '#FDE68A' },
    { label: 'Bullish', pct: bullishPct, color: '#10B981', track: '#D1FAE5', dot: '#6EE7B7' },
  ];

  return (
    <div className="space-y-3">
      {rows.map(({ label, pct, color, track, dot }) => (
        <div key={label}>
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full shrink-0" style={{ background: dot }} />
              <span className="text-[11px] font-semibold text-slate-700">{label}</span>
            </div>
            <span className="text-[13px] font-black tabular-nums" style={{ color }}>
              {pct}%
            </span>
          </div>
          <div className="w-full h-2 rounded-full overflow-hidden" style={{ background: track }}>
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{ width: `${pct}%`, background: color }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Overview tab ─────────────────────────────────────────────────────────────

function OverviewTab({ ticker }: { ticker: string }) {
  const { themes, loading: themesLoading } = useAIThemes(ticker);

  return (
    <div className="space-y-3 pt-1">

      {/* AI Themes */}
      <div className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3.5">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-6 h-6 rounded-md flex items-center justify-center text-xs shrink-0" style={{ background: '#E0E7FF' }}>
            ✦
          </div>
          <p className="text-xs font-bold text-slate-800">Extracted AI Themes</p>
        </div>
        {themesLoading ? (
          <div className="flex flex-wrap gap-1.5">
            {[80, 64, 96, 72, 56].map(w => (
              <div key={w} className="h-5 rounded-full animate-pulse"
                style={{ background: '#E5E7EB', minWidth: w }} />
            ))}
          </div>
        ) : themes.length === 0 ? (
          <p className="text-[11px] text-slate-400 italic">No themes found for {ticker}.</p>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {themes.map(t => (
              <span key={t}
                className="px-2 py-0.5 rounded-full text-[10px] font-medium border cursor-pointer hover:border-indigo-300 hover:bg-indigo-50 transition-colors"
                style={{ background: '#F9FAFB', color: '#374151', borderColor: '#E5E7EB' }}>
                {t}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Macro Market Context */}
      <MacroCard />

    </div>
  );
}

// ── News tab ──────────────────────────────────────────────────────────────────

function NewsTab({ ticker }: { ticker: string }) {
  const { items, loading, error } = useMarketNews(ticker);

  if (loading) {
    return (
      <div className="pt-1 space-y-2">
        {[1, 2, 3].map(i => (
          <div key={i} className="rounded-xl border border-slate-100 bg-white p-3.5 space-y-2">
            <div className="flex justify-between">
              <SkeletonLine w="w-24" h="h-2.5" />
              <SkeletonLine w="w-16" h="h-4" />
            </div>
            <SkeletonLine h="h-3.5" />
            <SkeletonLine w="w-4/5" h="h-3.5" />
            <SkeletonLine w="w-3/4" h="h-2.5" />
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="pt-4 text-center text-[12px] text-slate-400">
        Failed to load news. Please try again.
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="pt-4 text-center text-[12px] text-slate-400 italic">
        No recent news found for {ticker}.
      </div>
    );
  }

  return (
    <div className="pt-1 space-y-2">
      {items.map((article: MarketNewsItem, idx: number) => (
        <a
          key={idx}
          href={article.url ?? undefined}
          target={article.url ? '_blank' : undefined}
          rel="noopener noreferrer"
          className="block rounded-xl border border-slate-100 bg-white p-3.5 hover:border-slate-200 hover:bg-slate-50/50 transition-colors"
          style={{ cursor: article.url ? 'pointer' : 'default', textDecoration: 'none' }}
        >
          {/* Source + badge */}
          <div className="flex items-center justify-between gap-2 mb-1.5">
            <span className="text-[9px] font-semibold uppercase tracking-widest truncate text-slate-400">
              {[article.source, article.time_ago].filter(Boolean).join(' · ')}
            </span>
            <SentimentBadge sentiment={article.sentiment} />
          </div>

          {/* Title */}
          <h3 className="text-[12px] font-semibold leading-snug mb-1 line-clamp-2 text-slate-900">
            {article.title}
          </h3>

          {/* Summary */}
          <p className="text-[10px] leading-relaxed line-clamp-2 text-slate-500">
            {article.summary}
          </p>
        </a>
      ))}
    </div>
  );
}

// ── Main ─────────────────────────────────────────────────────────────────────

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'news',     label: 'News'     },
];

export default function Sentiment({ ticker = 'AAPL' }: { ticker?: string }) {
  const [activeTab, setActiveTab] = useState('overview');

  return (
    <div className="flex flex-col h-full antialiased text-slate-900">

      {/* Panel header */}
      <div className="shrink-0 px-4 pt-5 pb-3 border-b border-slate-100">
        <div className="flex items-baseline gap-2">
          <h1 className="text-base font-extrabold tracking-tight text-slate-900">Market Sentiment</h1>
          <span className="text-[11px] font-mono font-bold px-1.5 py-0.5 rounded"
            style={{ background: '#EEF2FF', color: '#4F46E5' }}>
            {ticker}
          </span>
        </div>
      </div>

      {/* Tab bar */}
      <div className="shrink-0 px-3 pt-3 pb-2">
        <div className="flex gap-0.5 p-1 bg-slate-100 rounded-xl no-scrollbar">
          {TABS.map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={`flex-1 px-2 py-1.5 text-[10px] font-bold rounded-lg whitespace-nowrap transition-all ${
                activeTab === tab.id
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700'
              }`}>
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto px-4 pb-6">
        {activeTab === 'overview'
          ? <OverviewTab ticker={ticker} />
          : <NewsTab    ticker={ticker} />
        }
      </div>

    </div>
  );
}
